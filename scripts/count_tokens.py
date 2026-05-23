#!/usr/bin/env python3
"""Count source-code tokens with tiktoken.

One invocation writes results/current.{md,json,csv}. Default scope counts
only benchmark source files, not package manifests, lockfiles, generated
files, or this script.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import tiktoken

from _common import LANGUAGES, TASKS, Language, scan_sources


# Column order for the markdown table and json totals; first-listed wins ties.
LANG_ORDER = [l.prompt_label for l in LANGUAGES]
SLUG_BY_LABEL = {l.prompt_label: l.slug for l in LANGUAGES}


@dataclass(frozen=True)
class Row:
    language: str
    example: str
    file: str
    lines: int
    chars: int
    tokens: int


def load_encoding(name: str):
    try:
        return tiktoken.get_encoding(name)
    except Exception as error:  # pragma: no cover - error text is environment-specific.
        raise SystemExit(
            "Could not load tiktoken encoding "
            f"{name!r}. tiktoken downloads encoder data on first use.\n"
            "Run once with internet access, or pre-populate TIKTOKEN_CACHE_DIR.\n"
            f"Original error: {error}"
        ) from error


def count_file(root: Path, lang: Language, task: str, path: Path, enc) -> Row:
    text = path.read_text(encoding="utf-8")
    return Row(
        language=lang.prompt_label,
        example=task,
        file=path.relative_to(root).as_posix(),
        lines=text.count("\n") + (0 if text.endswith("\n") else 1),
        chars=len(text),
        tokens=len(enc.encode(text)),
    )


def pivot(rows: list[Row]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        out.setdefault(row.example, {})[row.language] = row.tokens
    return out


def _winner(values: dict[str, int]) -> str:
    """Lang with smallest tokens. Tie-break: registry order (column-left wins)."""
    return min(LANG_ORDER, key=lambda lang: (values.get(lang, 10**9), LANG_ORDER.index(lang)))


def render_markdown(rows: list[Row]) -> str:
    by_example = pivot(rows)
    header = ["Example"] + [f"{l} tokens" for l in LANG_ORDER] + ["Winner"]
    sep = ["---"] + ["---:"] * len(LANG_ORDER) + ["---"]
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(sep) + "|"]
    totals = {l: 0 for l in LANG_ORDER}
    for example in sorted(by_example):
        values = by_example[example]
        cells = [example] + [str(values.get(l, "")) for l in LANG_ORDER] + [_winner(values)]
        lines.append("| " + " | ".join(cells) + " |")
        for l in LANG_ORDER:
            totals[l] += values.get(l, 0)
    total_cells = ["**Total**"] + [f"**{totals[l]}**" for l in LANG_ORDER] + [f"**{_winner(totals)}**"]
    lines.append("| " + " | ".join(total_cells) + " |")
    return "\n".join(lines) + "\n"


def render_json(rows: list[Row]) -> str:
    by_example = pivot(rows)
    examples = []
    totals = {l: 0 for l in LANG_ORDER}
    for example in sorted(by_example):
        values = by_example[example]
        row: dict[str, int | str] = {"task": example}
        for lang in LANG_ORDER:
            row[SLUG_BY_LABEL[lang]] = values.get(lang, 0)
            totals[lang] += values.get(lang, 0)
        row["winner"] = _winner(values)
        examples.append(row)
    payload = {
        "examples": examples,
        "totals": {SLUG_BY_LABEL[l]: totals[l] for l in LANG_ORDER},
        "totals_winner": _winner(totals),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_csv(rows: list[Row]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(Row.__dataclass_fields__))
    writer.writeheader()
    writer.writerows(asdict(row) for row in rows)
    return buf.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description="Count source-code tokens with tiktoken.")
    parser.add_argument("--root", default=".", help="Benchmark repo root")
    parser.add_argument("--encoding", default="o200k_base", help="tiktoken encoding name")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    enc = load_encoding(args.encoding)

    sources = scan_sources(root)
    rows: list[Row] = []
    for lang in LANGUAGES:
        for task in TASKS:
            path = sources[lang.slug][task]
            if not path.exists():
                continue
            rows.append(count_file(root, lang, task, path, enc))

    out_dir = root / "results"
    out_dir.mkdir(exist_ok=True)
    md = render_markdown(rows)
    (out_dir / "current.md").write_text(md, encoding="utf-8")
    (out_dir / "current.json").write_text(render_json(rows), encoding="utf-8")
    (out_dir / "current.csv").write_text(render_csv(rows), encoding="utf-8")

    sys.stdout.write(md)
    sys.stderr.write("\nwrote results/current.{md,json,csv}\n")


if __name__ == "__main__":
    main()
