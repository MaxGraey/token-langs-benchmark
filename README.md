# Token cost benchmark: Rust vs TypeScript vs Zig vs Go vs Python

A mini-benchmark for comparing how many input/output tokens are needed to write the same small program in Rust, TypeScript, Zig, Go and Python.

The goal is not to prove which language is "best", but to estimate token ergonomics for LLM code generation: how much text is needed to write readable, idiomatic, typed code.

## What's inside

```text
scripts/count_tokens.py          # tiktoken-based counter
requirements.txt                 # Python deps for the counter
results/baseline_snapshot.*      # snapshot from the current comparison
rust/src/bin/*.rs                # Rust examples
typescript/src/*.ts              # TypeScript examples
zig/src/*.zig                    # Zig examples
go/cmd/*/main.go                 # Go examples (one binary per task subdir)
go/go.mod                        # Go module manifest
python/src/*.py                  # Python examples
python/requirements.txt          # Python runtime deps (FastAPI for http-rest)
```

## Versions used for the snapshot

- Rust stable 1.95.0
- TypeScript 7.0 Beta via `@typescript/native-preview@beta` / `tsgo`
- Zig 0.16.0
- Go 1.26
- Python 3.12+ (FastAPI 0.115, uvicorn 0.32 for the http-rest example)
- Counter: `tiktoken==0.12.0`
- Tokenizer: `o200k_base`

## Baseline table

This is the baseline from the current comparison. After unpacking, it is better to recalculate locally, because `tiktoken` and the selected encoding may produce slightly different numbers.

| Example | Rust tokens | TypeScript tokens | Zig tokens | Go tokens | Python tokens | Winner |
|---|---:|---:|---:|---:|---:|---|
| find-prime-numbers | 102 | 103 | 166 | 114 | 86 | Python |
| http-rest | 391 | 165 | 576 | 346 | 202 | TypeScript |
| json-parser | 1157 | 763 | 1205 | 618 | 497 | Python |
| word-frequency | 152 | 129 | 368 | 234 | 76 | Python |
| **Total** | **1802** | **1160** | **2315** | **1312** | **861** | **Python** |

Relative to Python (the current overall winner):

| Language | Total tokens | Ratio vs Python |
|---|---:|---:|
| Python | 861 | 1.00x |
| TypeScript | 1160 | 1.35x |
| Go | 1312 | 1.52x |
| Rust | 1802 | 2.09x |
| Zig | 2315 | 2.69x |

## Install the tokenizer benchmark

```bash
pip install -r requirements.txt
```

`tiktoken` usually downloads the encoding file on the first run and then loads it from cache. For fully reproducible runs, you can pin the cache directory:

```bash
export TIKTOKEN_CACHE_DIR="$PWD/.tiktoken-cache"
python scripts/count_tokens.py --encoding o200k_base
```

## Run token counting

One command writes `results/current.{md,json,csv}` and prints the markdown table to stdout:

```bash
python scripts/count_tokens.py --encoding o200k_base
```

By default, the script counts only source files under the registered language roots:

```text
rust/src/bin
typescript/src
zig/src
go/cmd
python/src
```

Manifests such as `Cargo.toml`, `package.json`, `build.zig`, `go.mod`, `requirements.txt`, lockfiles and the README are intentionally excluded.

## Install Rust toolchain

See <https://www.rust-lang.org/tools/install>

## Install TypeScript deps

```bash
cd typescript
npm install
```

## Install Zig toolchain

See <https://ziglang.org/learn/getting-started>

## Install Go toolchain

See <https://go.dev/doc/install>

## Install Python deps

```bash
pip install -r python/requirements.txt
```

## Methodology

The benchmark tries to keep the code:

- compact, but still readable;
- idiomatic enough for each language;
- typed in a way a human would likely write;
- free of explicit return type annotations where the language reasonably allows it;
- comparable by task, not by exact AST structure.

The four examples are:

1. `find-prime-numbers` - a basic numeric loop and collection.
2. `http-rest` - a simple REST API with list/get/create users.
3. `json-parser` - a tiny handwritten JSON parser, with no non-standard parser libraries.
4. `word-frequency` - a small text pipeline with grouping, sorting and top-k output.
