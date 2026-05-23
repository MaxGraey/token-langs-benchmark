# Cross-language LLM code benchmark: tokens and perplexity

A mini-benchmark for comparing programming languages on two LLM-relevant axes: how many tokens each idiomatic implementation costs, and how many bits a small code LM needs to generate it. The current snapshot covers Rust, TypeScript, Zig, Go and Python, but the language set is open - adding a new one is a single registry entry.

The goal is not to prove which language is "best", but to estimate ergonomics for LLM code generation: how much text is needed, and how predictable that text is to a code model.

## Versions used for the snapshot

- Rust stable 1.95.0
- TypeScript 7.0 Beta via `@typescript/native-preview@beta` / `tsgo`
- Zig 0.16.0
- Go 1.26
- Python 3.12+ (FastAPI 0.115, uvicorn 0.32 for the http-rest example)
- Counter: `tiktoken==0.13.0`
- Tokenizer: `o200k_base`

## Metrics

Two complementary metrics, both run over the same reference implementations.

**Token count** (`scripts/count_tokens.py`): length of each implementation under the `o200k_base` tokenizer. Tokenizer-only, language-agnostic, no model weights needed. Proxies the raw input/output cost charged by token-billed LLM APIs.

**Perplexity bits** (`scripts/score_perplexity.py`, see "Perplexity baseline" below): how many bits a small code LM needs to generate each implementation given a per-task prompt. The prompt is held fixed and only the code tokens are scored:

$$
\mathrm{total\_bits} \;=\; \sum_{i=1}^{N} -\log_2 p\!\left(t_i \mid t_{<i}\right)
$$

where $t_1, \ldots, t_N$ are the code tokens and the conditioning $t_{<i}$ includes the prompt tokens. For cross-task aggregation we report bits per UTF-8 byte (the Code Llama / Qwen2.5-Coder convention), with perplexity derived from the average:

$$
\mathrm{bpb} \;=\; \frac{\mathrm{total\_bits}}{\mathrm{byte\_len}} \qquad\qquad \mathrm{PPL} \;=\; 2^{\,\mathrm{total\_bits}\,/\,N}
$$

The two metrics can disagree: a verbose-but-predictable implementation may cost more tokens but fewer bits, and vice versa.

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

## Install the tokenizer benchmark

```bash
pip3 install -r requirements.txt
```

`tiktoken` usually downloads the encoding file on the first run and then loads it from cache. For fully reproducible runs, you can pin the cache directory:

```bash
export TIKTOKEN_CACHE_DIR="$PWD/.tiktoken-cache"
python3 scripts/count_tokens.py --encoding o200k_base
```

## Run token counting

One command writes `results/current.{md,json,csv}` and prints the markdown table to stdout:

```bash
python3 scripts/count_tokens.py --encoding o200k_base
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
pip3 install -r python/requirements.txt
```
