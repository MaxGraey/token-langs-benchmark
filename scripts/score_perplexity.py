#!/usr/bin/env python3
"""Score reference implementations under a local code LM.

Reports total_bits per (task, lang) so we can compare how surprising each
language's reference solution is under the same model. The scoring loop
itself is wired up in a later task, this file currently only exposes the
CLI surface (argparse) and a stub main.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

from _common import LANGUAGES, TASKS


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
