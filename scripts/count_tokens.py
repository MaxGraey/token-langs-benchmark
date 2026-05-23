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
from typing import Callable, Iterable

import tiktoken


# Single source of truth for per-language knobs. Add a language by
# appending one entry; column order in the markdown table follows this list.
# example_for: how to derive the task slug from a source path
#   - default (path.stem) for flat layouts: rust/src/bin/find_prime_numbers.rs
#   - parent.name for nested layouts: go/cmd/find_prime_numbers/main.go
@dataclass(frozen=True)
class Language:
    suffix: str
    name: str
    root: str
    example_for: Callable[[Path], str]


LANGUAGES: tuple[Language, ...] = (
    Language(".rs",  "Rust",       "rust/src/bin",   lambda p: p.stem),
    Language(".ts",  "TypeScript", "typescript/src", lambda p: p.stem),
    Language(".zig", "Zig",        "zig/src",        lambda p: p.stem),
    Language(".go",  "Go",         "go/cmd",         lambda p: p.parent.name),
    Language(".py",  "Python",     "python/src",     lambda p: p.stem),
)

LANG_BY_SUFFIX = {l.suffix: l for l in LANGUAGES}
SUFFIXES = set(LANG_BY_SUFFIX)
DEFAULT_ROOTS = [l.root for l in LANGUAGES]
LANG_ORDER = [l.name for l in LANGUAGES]


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


def iter_sources(root: Path, roots: Iterable[str]) -> Iterable[Path]:
    for rel in roots:
        base = root / rel
        if not base.exists():
            continue
        yield from sorted(path for path in base.rglob("*") if path.suffix in SUFFIXES)


def count_file(root: Path, path: Path, enc) -> Row:
    lang = LANG_BY_SUFFIX[path.suffix]
    text = path.read_text(encoding="utf-8")
    return Row(
        language=lang.name,
        example=lang.example_for(path).replace("_", "-"),
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
    # NOTE: lang.lower() doubles as the future slug key. When the LANGUAGES
    # registry moves to scripts/_common.py (per the perplexity design plan)
    # and gains an explicit `slug` field, replace .lower() with .slug.
    by_example = pivot(rows)
    examples = []
    totals = {l: 0 for l in LANG_ORDER}
    for example in sorted(by_example):
        values = by_example[example]
        row = {"task": example}
        for lang in LANG_ORDER:
            row[lang.lower()] = values.get(lang, 0)
            totals[lang] += values.get(lang, 0)
        row["winner"] = _winner(values)
        examples.append(row)
    payload = {
        "examples": examples,
        "totals": {l.lower(): totals[l] for l in LANG_ORDER},
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
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="Benchmark repo root")
    parser.add_argument("--encoding", default="o200k_base", help="tiktoken encoding name")
    parser.add_argument("--roots", nargs="*", default=DEFAULT_ROOTS, help="Source roots to scan")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    enc = load_encoding(args.encoding)
    rows = [count_file(root, path, enc) for path in iter_sources(root, args.roots)]

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
