#!/usr/bin/env python3
"""Score reference implementations under a local code LM.

Reports total_bits per (task, lang) so we can compare how surprising each
language's reference solution is under the same model. The scoring loop
itself is wired up in a later task, this file currently only exposes the
CLI surface (argparse) and a stub main.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import List, Optional, Protocol, Tuple

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
