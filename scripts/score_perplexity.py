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
import io
import json as json_lib
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple

import numpy as np

from _common import LANGUAGES, TASKS


# math has no LN2 / LOG2E constant, cache log2(e) = 1/ln(2) to convert
# natural-log results to log2 by multiplication (one less div per token).
_LOG2E = math.log2(math.e)


class Scorer(Protocol):
    """Minimal surface llama-cpp-python exposes that we need.

    Real impl wraps Llama, tests provide a FakeScorer with hand-crafted
    logits. `prefill` runs a forward pass over the given tokens and
    populates `scores`.
    """
    scores: "np.ndarray"

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
    avg_nll: float
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
    for task in sorted(groups):
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
    agg_cells = ["**Aggregate bpb**"]
    for lang in LANGUAGES:
        agg_cells += [f"{sums[lang.slug]['bits']:.1f}", f"**{per_lang_bpb[lang.slug]:.3f}**"]
    agg_cells.append(min(LANGUAGES, key=lambda lang: (per_lang_bpb[lang.slug], lang.slug)).slug)
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
                     "avg_nll", "ppl", "prompt_sha256"])
    for r in rows:
        writer.writerow([r.task, r.lang, r.tokens, r.byte_len,
                         f"{r.total_bits:.6f}", f"{r.bpb:.6f}",
                         f"{r.avg_nll:.6f}", f"{r.ppl:.6f}", r.prompt_sha256])
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
    parser.add_argument("--format", choices=["md", "json", "csv"], default="md")
    parser.add_argument("--n-ctx", type=int, default=8192)
    parser.add_argument("--n-threads", type=int, default=None,
                        help="Default: physical core count")
    parser.add_argument("--task", action="append", default=[], choices=list(TASKS),
                        help="Filter by task name (repeatable)")
    parser.add_argument("--lang", action="append", default=[], choices=lang_choices,
                        help="Filter by language slug (repeatable)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Default: stdout")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    raise NotImplementedError("TODO")


if __name__ == "__main__":
    raise SystemExit(main())
