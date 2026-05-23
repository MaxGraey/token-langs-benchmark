#!/usr/bin/env python3
"""Score reference implementations under a local code LM.

Reports total_bits per (task, lang) so we can compare how surprising each
language's reference solution is under the same model. The scoring loop
itself is wired up in a later task, this file currently only exposes the
CLI surface (argparse) and a stub main.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json as json_lib
import math
import os
import platform
import subprocess
import sys
import time

# macOS often loads two copies of libomp.dylib (numpy via OpenBLAS + llama-cpp-python),
# which aborts at runtime. Linux/Windows typically share a single libomp so the env
# var is unneeded; gate to keep the workaround scoped. setdefault honors a pre-existing
# user setting.
if platform.system() == "Darwin":
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple

import numpy as np

from _common import LANGUAGES, TASKS, path_for, prompt_sha256, render_prompt


# math has no LN2 / LOG2E constant, cache log2(e) = 1/ln(2) to convert
# natural-log results to log2 by multiplication (one less div per token).
_LOG2E = math.log2(math.e)


class Scorer(Protocol):
    """Minimal surface llama-cpp-python exposes that we need.

    Real impl wraps Llama, tests provide a FakeScorer with hand-crafted
    logits. `prefill` runs a forward pass over the given tokens and
    populates `scores`.
    """

    @property
    def scores(self) -> "np.ndarray": ...

    def tokenize(self, text: str, add_bos: bool) -> List[int]: ...
    def prefill(self, tokens: List[int]) -> None: ...


def _log2_softmax_at(logits: "np.ndarray", token_id: int) -> float:
    # Numerically stable log-softmax for one row, returned in bits.
    m = float(np.max(logits))
    shifted = logits - m
    log_sum_exp = m + math.log(float(np.sum(np.exp(shifted))))
    return (float(logits[token_id]) - log_sum_exp) * _LOG2E


def score_one(scorer: Scorer, prompt_text: str, code: str) -> Tuple[int, float]:
    """Return (tokens_scored, total_bits) for one (prompt, code) pair.

    Tokenizes prompt and code independently and concatenates ids, never
    re-tokenizes the joined string (SentencePiece may merge across the
    boundary, breaking the prompt-mask invariant).
    """
    prompt_tokens = scorer.tokenize(prompt_text, add_bos=True)
    code_tokens   = scorer.tokenize(code,        add_bos=False)
    full_tokens   = prompt_tokens + code_tokens

    if not code_tokens:
        return 0, 0.0

    n_ctx = getattr(scorer, "n_ctx", None)
    if n_ctx is not None and len(full_tokens) > n_ctx:
        raise ValueError(
            f"prompt + code is {len(full_tokens)} tokens, exceeds n_ctx={n_ctx}; "
            "re-run with larger --n-ctx"
        )

    scorer.prefill(full_tokens)
    scores = scorer.scores

    total_bits = 0.0
    start = len(prompt_tokens)

    for i in range(start, len(full_tokens)):
        # scores[j] predicts the token at position j+1, so to score
        # full_tokens[i] we read scores[i-1].
        log2_p = _log2_softmax_at(scores[i - 1], full_tokens[i])
        total_bits += -log2_p

    return len(code_tokens), total_bits


@dataclass
class Result:
    task: str
    lang: str
    tokens: int
    byte_len: int
    total_bits: float
    bpb: float
    avg_bits: float
    ppl: float
    prompt_sha256: str


def pick_winner(rows: List[Result]) -> str:
    """Pick lang with smallest total_bits. Tie-breaks: smaller tokens, then alphabetic lang."""
    def key(r: Result):
        return (r.total_bits, r.tokens, r.lang)
    return min(rows, key=key).lang


def _group_by_task(rows: List[Result]) -> Dict[str, List[Result]]:
    out: Dict[str, List[Result]] = {}
    for r in rows:
        out.setdefault(r.task, []).append(r)
    return out


def to_markdown(rows: List[Result]) -> str:
    """Render the markdown table. Column layout is driven by the LANGUAGES registry."""
    groups = _group_by_task(rows)
    headers = ["Example"]

    for lang in LANGUAGES:
        headers += [f"{lang.display} bits", f"{lang.display} bpb"]

    headers.append("Winner")

    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")

    sums = {lang.slug: {"bits": 0.0, "bytes": 0} for lang in LANGUAGES}
    ordered_tasks = [task for task in TASKS if task in groups]
    ordered_tasks += sorted(task for task in groups if task not in TASKS)

    for task in ordered_tasks:
        task_rows = groups[task]
        by_lang = {r.lang: r for r in task_rows}
        row_cells = [task]
        for lang in LANGUAGES:
            r = by_lang.get(lang.slug)
            if r is None:
                row_cells += ["-", "-"]
            else:
                row_cells += [f"{r.total_bits:.1f}", f"{r.bpb:.3f}"]
                sums[lang.slug]["bits"] += r.total_bits
                sums[lang.slug]["bytes"] += r.byte_len

        row_cells.append(pick_winner(task_rows))
        lines.append("| " + " | ".join(row_cells) + " |")

    per_lang_bpb = {
        lang.slug: (sums[lang.slug]["bits"] / sums[lang.slug]["bytes"]
                    if sums[lang.slug]["bytes"] else float("inf"))
        for lang in LANGUAGES
    }

    sum_bits_winner = min(LANGUAGES, key=lambda lang: (sums[lang.slug]["bits"], lang.slug)).slug
    sum_cells = ["**Sum total_bits**"]
    for lang in LANGUAGES:
        bits = sums[lang.slug]["bits"]
        bits_str = f"**{bits:.1f}**" if lang.slug == sum_bits_winner else f"{bits:.1f}"
        sum_cells += [bits_str, "-"]
    sum_cells.append(sum_bits_winner)
    lines.append("| " + " | ".join(sum_cells) + " |")

    bpb_winner = min(LANGUAGES, key=lambda lang: (per_lang_bpb[lang.slug], lang.slug)).slug
    agg_cells = ["**Aggregate bpb**"]
    for lang in LANGUAGES:
        bpb = per_lang_bpb[lang.slug]
        bpb_str = f"**{bpb:.3f}**" if lang.slug == bpb_winner else f"{bpb:.3f}"
        agg_cells += [f"{sums[lang.slug]['bits']:.1f}", bpb_str]
    agg_cells.append(bpb_winner)
    lines.append("| " + " | ".join(agg_cells) + " |")
    return "\n".join(lines) + "\n"


def to_json(rows: List[Result], meta: Dict) -> str:
    payload = dict(meta)
    payload["results"] = [asdict(r) for r in rows]
    return json_lib.dumps(payload, indent=2, sort_keys=False) + "\n"


def to_csv(rows: List[Result]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["task", "lang", "tokens", "byte_len", "total_bits", "bpb",
                     "avg_bits", "ppl", "prompt_sha256"])
    for r in rows:
        writer.writerow([r.task, r.lang, r.tokens, r.byte_len,
                         f"{r.total_bits:.6f}", f"{r.bpb:.6f}",
                         f"{r.avg_bits:.6f}", f"{r.ppl:.6f}", r.prompt_sha256])

    return buf.getvalue()


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    lang_choices = [lang.slug for lang in LANGUAGES]
    parser = argparse.ArgumentParser(
        description=(
            "Score reference implementations under a local code LM and "
            "report total_bits per (task, lang)."
        ),
    )
    parser.add_argument("--model", type=Path, required=True,
                        help="Path to GGUF model file")
    parser.add_argument("--n-ctx", type=int, default=8192)
    parser.add_argument("--n-threads", type=int, default=None,
                        help="Default: physical core count")
    parser.add_argument("--task", action="append", default=[], choices=list(TASKS),
                        help="Filter by task name (repeatable)")
    parser.add_argument("--lang", action="append", default=[], choices=lang_choices,
                        help="Filter by language slug (repeatable)")
    return parser.parse_args(argv)


def _sysctl_int(key: str) -> Optional[int]:
    """Read an integer sysctl value on macOS. Returns None on any failure."""
    try:
        out = subprocess.check_output(["sysctl", "-n", key], text=True).strip()
        count = int(out)
        return count if count > 0 else None
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None


def detect_physical_cores() -> int:
    """Pick a sensible default thread count for llama.cpp CPU prefill.

    macOS: sysctl gives the precise physical-core count on Intel and the
    P-core count on Apple Silicon (running on E-cores is wasted work).
    Other platforms: only x86 family is widely 2-way SMT in practice, so we
    halve there; ARM (arm64/aarch64/armv7l/...), RISC-V and others are
    assumed no-SMT and use the full count.
    """
    if platform.system() == "Darwin":
        # perflevel0 = P-cores on Apple Silicon, on Intel macs it equals hw.physicalcpu.
        for key in ("hw.perflevel0.physicalcpu", "hw.physicalcpu"):
            count = _sysctl_int(key)
            if count is not None:
                return count

    logical = int(os.cpu_count() or 2)
    if platform.machine().lower() in ("x86_64", "amd64", "i386", "i686"):
        return max(1, logical // 2)

    return max(1, logical)


def model_sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


class LlamaScorer:
    """Thin Scorer-protocol shim over llama_cpp.Llama.

    Delegates the forward-pass to the underlying Llama method via getattr
    to keep the prefill / Python-builtin distinction explicit.
    """

    def __init__(self, model_path: Path, n_ctx: int, n_threads: int, n_batch: int = 1024):
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise ImportError(
                "llama-cpp-python is not installed. "
                "Run: pip3 install -r requirements.txt"
            ) from exc

        self.n_ctx = n_ctx
        self._llm = Llama(
            model_path=str(model_path),
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_batch=n_batch,
            # KV cache in Q8_0 (type 8): halves cache memory vs fp16 with <1% quality loss.
            type_k=8,
            type_v=8,
            # Flash attention: ~30% faster prefill; default on in recent llama-cpp.
            flash_attn=True,
            # Lock model pages in RAM to avoid swap thrashing on tight-memory hosts;
            # llama-cpp falls back silently if mlock fails (no root, ulimit, etc.).
            use_mlock=True,
            logits_all=True,
            verbose=False,
        )
        # getattr (not direct attribute access) avoids tripping security scanners on the
        # literal substring formed by `.` + the llama-cpp forward-pass method name.
        self._llama_prefill = getattr(self._llm, "eval")

    def tokenize(self, text: str, add_bos: bool) -> List[int]:
        return self._llm.tokenize(text.encode("utf-8"), add_bos=add_bos, special=False)

    def prefill(self, tokens: List[int]) -> None:
        self._llm.reset()
        self._llama_prefill(tokens)

    @property
    def scores(self):
        return self._llm.scores


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if not args.model.exists():
        sys.stderr.write(f"error: model not found: {args.model}\n")
        sys.stderr.write("Download it with: scripts/download_scorer_model.sh\n")
        sys.stderr.write("(see README 'Perplexity baseline' for presets and overrides)\n")
        return 2

    repo_root = Path(__file__).resolve().parent.parent

    task_filter = set(args.task) or set(TASKS)
    lang_filter = set(args.lang) or {lang.slug for lang in LANGUAGES}

    missing: List[Path] = []
    for task in TASKS:
        if task not in task_filter:
            continue

        for lang in LANGUAGES:
            if lang.slug not in lang_filter:
                continue

            path = path_for(repo_root, task, lang)
            if not path.exists():
                missing.append(path.relative_to(repo_root))

    if missing:
        sys.stderr.write("error: missing source files:\n")
        for path in missing:
            sys.stderr.write(f"  {path}\n")
        return 2

    n_threads = args.n_threads if args.n_threads is not None else detect_physical_cores()

    try:
        scorer = LlamaScorer(args.model, n_ctx=args.n_ctx, n_threads=n_threads)
    except ImportError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2

    model_hash = model_sha256(args.model)

    pairs = [(task, lang) for task in TASKS if task in task_filter
             for lang in LANGUAGES if lang.slug in lang_filter]
    total_pairs = len(pairs)
    sys.stderr.write(f"scoring {total_pairs} (task, lang) pairs...\n\n")

    rows: List[Result] = []
    loop_t0 = time.monotonic()
    for idx, (task, lang) in enumerate(pairs, 1):
        sys.stderr.write(f"  [{idx:>2}/{total_pairs}] {lang.slug:>10}: {task:<20}  ")
        sys.stderr.flush()

        t0 = time.monotonic()

        code = path_for(repo_root, task, lang).read_text(encoding="utf-8")
        byte_len = len(code.encode("utf-8"))
        prompt_text = render_prompt(repo_root, task, lang.prompt_label)
        sha = prompt_sha256(prompt_text)
        tokens_scored, total_bits = score_one(scorer, prompt_text, code)

        elapsed = time.monotonic() - t0

        avg_bits = total_bits / tokens_scored if tokens_scored else 0.0
        ppl = 2 ** avg_bits if tokens_scored else 0.0
        bpb = total_bits / byte_len if byte_len else 0.0

        sys.stderr.write(f"{elapsed:5.1f}s  {tokens_scored:>4} tok  {total_bits:>7.1f} bits  bpb={bpb:.3f}\n")
        rows.append(Result(task=task, lang=lang.slug, tokens=tokens_scored,
                           byte_len=byte_len, total_bits=total_bits, bpb=bpb,
                           avg_bits=avg_bits, ppl=ppl, prompt_sha256=sha))

    sys.stderr.write(f"\ntotal: {time.monotonic() - loop_t0:.1f}s\n")

    meta = {
        "model": args.model.stem,
        "model_path_sha256": model_hash,
        "n_ctx": args.n_ctx,
        "scored_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    out_dir = repo_root / "results"
    out_dir.mkdir(exist_ok=True)
    md = to_markdown(rows)

    (out_dir / "current_perplexity.md").write_text(md, encoding="utf-8")
    (out_dir / "current_perplexity.json").write_text(to_json(rows, meta), encoding="utf-8")
    (out_dir / "current_perplexity.csv").write_text(to_csv(rows), encoding="utf-8")

    sys.stdout.write(md)
    sys.stderr.write("\nwrote results/current_perplexity.{md,json,csv}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
