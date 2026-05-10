#!/usr/bin/env python3
"""Count source-code tokens with tiktoken.

Default scope intentionally counts only benchmark source files, not package
manifests, lockfiles, generated files, or this script.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import tiktoken

DEFAULT_ROOTS = ["rust/src/bin", "zig/src", "typescript/src"]
SOURCE_SUFFIXES = {".rs", ".zig", ".ts"}
LANG_BY_SUFFIX = {".rs": "Rust", ".zig": "Zig", ".ts": "TypeScript"}


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
        yield from sorted(path for path in base.rglob("*") if path.suffix in SOURCE_SUFFIXES)


def example_name(path: Path) -> str:
    return path.stem.replace("_", "-")


def count_file(root: Path, path: Path, enc) -> Row:
    text = path.read_text(encoding="utf-8")
    return Row(
        language=LANG_BY_SUFFIX[path.suffix],
        example=example_name(path),
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


def print_markdown(rows: list[Row]) -> None:
    by_example = pivot(rows)
    languages = ["Rust", "TypeScript", "Zig"]
    print("| Example | Rust | TypeScript | Zig | Winner |")
    print("|---|---:|---:|---:|---|")
    for example in sorted(by_example):
        values = by_example[example]
        winner = min(languages, key=lambda lang: values.get(lang, 10**9))
        cells = [str(values.get(lang, "")) for lang in languages]
        print(f"| {example} | {cells[0]} | {cells[1]} | {cells[2]} | {winner} |")

    print("\n| Language | Lines | Chars | Tokens |")
    print("|---|---:|---:|---:|")
    for lang in languages:
        subset = [row for row in rows if row.language == lang]
        print(
            f"| {lang} | {sum(row.lines for row in subset)} | "
            f"{sum(row.chars for row in subset)} | {sum(row.tokens for row in subset)} |"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Benchmark repo root")
    parser.add_argument("--encoding", default="o200k_base", help="tiktoken encoding name")
    parser.add_argument("--roots", nargs="*", default=DEFAULT_ROOTS, help="Source roots to scan")
    parser.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    enc = load_encoding(args.encoding)
    rows = [count_file(root, path, enc) for path in iter_sources(root, args.roots)]

    if args.format == "markdown":
        print_markdown(rows)
    elif args.format == "json":
        print(json.dumps([asdict(row) for row in rows], indent=2, ensure_ascii=False))
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=list(Row.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


if __name__ == "__main__":
    main()
