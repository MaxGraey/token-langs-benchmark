# Token cost benchmark: Rust vs Zig vs TypeScript

A mini-benchmark for comparing how many input/output tokens are needed to write the same small program in Rust, Zig, and TypeScript.

The goal is not to prove which language is "best", but to estimate token ergonomics for LLM code generation: how much text is needed to write readable, idiomatic, typed code.

## What's inside

```text
scripts/count_tokens.py          # tiktoken-based counter
requirements.txt                 # Python deps
results/baseline_snapshot.*      # snapshot from the original comparison
rust/src/bin/*.rs                # Rust examples
zig/src/*.zig                    # Zig examples
typescript/src/*.ts              # TypeScript examples
```

## Versions used for the snapshot

- Rust stable 1.95.0
- Zig 0.16.0
- TypeScript 7.0 Beta via `@typescript/native-preview@beta` / `tsgo`
- Python `tiktoken==0.12.0`
- Tokenizer: `o200k_base`

## Baseline table

This is the baseline from the first run. After unpacking, it is better to recalculate locally, because `tiktoken` and the selected encoding may produce slightly different numbers.

| Example | Rust tokens | TypeScript tokens | Zig tokens | Winner |
|---|---:|---:|---:|---|
| find-prime-numbers | 158 | 133 | 266 | TypeScript |
| http-rest | 422 | 171 | 535 | TypeScript |
| json-parser | 963 | 622 | 1021 | TypeScript |
| word-frequency | 150 | 123 | 305 | TypeScript |
| **Total** | **1693** | **1049** | **2127** | **TypeScript** |

Relative to TypeScript:

| Language | Total tokens | Ratio vs TypeScript |
|---|---:|---:|
| TypeScript | 1049 | 1.00x |
| Rust | 1693 | 1.61x |
| Zig | 2127 | 2.03x |

## Install the tokenizer benchmark

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`tiktoken` usually downloads the encoding file on the first run and then loads it from cache. For fully reproducible runs, you can pin the cache directory:

```bash
export TIKTOKEN_CACHE_DIR="$PWD/.tiktoken-cache"
python scripts/count_tokens.py --encoding o200k_base
```

## Run token counting

Markdown table:

```bash
python scripts/count_tokens.py --encoding o200k_base
```

JSON:

```bash
python scripts/count_tokens.py --encoding o200k_base --format json > results/current.json
```

CSV:

```bash
python scripts/count_tokens.py --encoding o200k_base --format csv > results/current.csv
```

By default, the script counts only source files under:

```text
rust/src/bin
zig/src
typescript/src
```

Manifests such as `Cargo.toml`, `package.json`, `build.zig`, lockfiles, and the README are intentionally excluded.

## Install and run the Rust examples

```bash
rustup update stable
cd rust
cargo run --bin find_prime_numbers
cargo run --bin word_frequency
cargo run --bin json_parser
cargo run --bin http_rest
```

The HTTP server starts on `127.0.0.1:3000`.

```bash
curl http://127.0.0.1:3000/users
curl -X POST http://127.0.0.1:3000/users \
  -H 'content-type: application/json' \
  -d '{"name":"Ada"}'
```

## Install and run the TypeScript examples

```bash
cd typescript
npm install
npm run check
npm run run:primes
npm run run:words
npm run run:json
npm run start:http
```

Notes:

- `find-prime-numbers.ts` and `word-frequency.ts` use ES2025 iterator helpers.
- The runtime must support iterator helpers or provide a polyfill.
- Type checking uses `tsgo` from the TypeScript 7 native preview.

The HTTP server starts on `127.0.0.1:3000`.

```bash
curl http://127.0.0.1:3000/users
curl -X POST http://127.0.0.1:3000/users \
  -H 'content-type: application/json' \
  -d '{"name":"Ada"}'
```

## Install and run the Zig examples

```bash
zig version
cd zig
zig run src/find_prime_numbers.zig
zig run src/word_frequency.zig
zig run src/json_parser.zig
```

`src/http_rest.zig` is included in token counting as the comparable HTTP REST shape. It uses an `httpz`-style API, but Zig package metadata changes quickly, so wire the exact current dependency in `build.zig.zon` before running that file.

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
4. `word-frequency` - a small text pipeline with grouping, sorting, and top-k output.

## Expected interpretation

The first snapshot had this ordering:

```text
TypeScript < Rust < Zig
```

That mostly reflects syntax and runtime/library ergonomics:

- TypeScript compresses data manipulation very aggressively through object literals, closures, structural typing, and iterator helpers.
- Rust pays for explicit data modeling, `Result`, ownership-friendly signatures, and framework extractor types.
- Zig pays a larger systems-language tax: allocators, ownership, manual containers, error unions, and cleanup.
