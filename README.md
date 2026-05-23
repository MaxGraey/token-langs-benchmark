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

## Toolchains

- **Rust:** <https://www.rust-lang.org/tools/install>
- **Zig:** <https://ziglang.org/learn/getting-started>
- **Go:** <https://go.dev/doc/install>
- **TypeScript example:** `cd typescript && npm install`
- **Python example runtime (FastAPI for http-rest):** `pip3 install -r python/requirements.txt`

## Metrics

Two complementary metrics, both run over the same reference implementations.

**Token count** (`scripts/count_tokens.py`): length of each implementation under the `o200k_base` tokenizer. Tokenizer-only, language-agnostic, no model weights needed. *Impact:* direct dollar cost on token-billed APIs (each input + output token is line-item billable) and decoding latency (autoregressive generation costs roughly one forward pass per token, so wall-clock time scales linearly).

**Perplexity bits** (`scripts/score_perplexity.py`, see "Perplexity baseline" below): how many bits a small code LM needs to generate each implementation given a per-task prompt. The prompt is held fixed and only the code tokens are scored:

$$
\mathrm{total\_bits} \;=\; \sum_{i=1}^{N} -\log_2 p\!\left(t_i \mid t_{<i}\right)
$$

where $t_1, \ldots, t_N$ are the code tokens and the conditioning $t_{<i}$ includes the prompt tokens. For cross-task aggregation we report bits per UTF-8 byte (the Code Llama / Qwen2.5-Coder convention), with perplexity derived from the average:

$$
\mathrm{bpb} \;=\; \frac{\mathrm{total\_bits}}{\mathrm{byte\_len}} \qquad\qquad \mathrm{PPL} \;=\; 2^{\,\mathrm{total\_bits}\,/\,N}
$$

*Impact:* lower bits mean the LM is more confident in this code shape, so first-shot correctness rises and retry / regeneration cost falls. Does not directly change per-call billing the way token count does, but compounds with it: high perplexity inflates the *effective* token budget because more attempts are needed before useful output appears.

The two metrics can disagree: a verbose-but-predictable implementation may cost more tokens but fewer bits, and vice versa. Token count is the visible price tag; perplexity is the implicit quality / first-shot-correctness signal.

## Baseline table

Token counts depend on the `tiktoken` version and selected encoding; recalculate locally for exact numbers.

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

## Perplexity baseline table

Bits and bits-per-byte under base Qwen2.5-Coder-3B Q5_K_M. Lower = the LM is more confident in the code shape (fewer expected retries / regenerations). Per-row Winner is the lang with smallest `total_bits`; the Aggregate row's Winner is the lang with smallest byte-weighted `bpb`.

| Example | Rust bits | Rust bpb | TS bits | TS bpb | Zig bits | Zig bpb | Go bits | Go bpb | Py bits | Py bpb | Winner |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| find-prime-numbers | 77.4 | 0.210 | 118.5 | 0.388 | 100.0 | 0.194 | 58.2 | 0.188 | 76.7 | 0.302 | Go |
| http-rest | 152.6 | 0.106 | 104.6 | 0.180 | 339.1 | 0.166 | 113.4 | 0.099 | 110.0 | 0.153 | TypeScript |
| json-parser | 468.8 | 0.107 | 458.1 | 0.172 | 550.7 | 0.115 | 235.7 | 0.135 | 252.1 | 0.125 | Go |
| word-frequency | 163.0 | 0.289 | 216.9 | 0.537 | 355.2 | 0.259 | 189.0 | 0.253 | 168.2 | 0.582 | Rust |
| **Aggregate bpb** | 861.9 | **0.127** | 898.1 | **0.227** | 1345.0 | **0.155** | 596.3 | **0.151** | 607.0 | **0.185** | **Rust** |

Relative to Rust (the current aggregate-bpb winner):

| Language | Aggregate bpb | Ratio vs Rust |
|---|---:|---:|
| Rust | 0.127 | 1.00x |
| Go | 0.151 | 1.19x |
| Zig | 0.155 | 1.22x |
| Python | 0.185 | 1.46x |
| TypeScript | 0.227 | 1.79x |

The token leaderboard (Python first) and the perplexity leaderboard (Rust first) **disagree**: Python is the cheapest to emit in tokens, but Rust is the most predictable shape per UTF-8 byte. Both numbers matter for production cost - tokens map to billing, perplexity maps to first-shot correctness.

## Methodology

Both metrics run over the same reference implementations; see Metrics above for the math. The code itself aims to be:

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

## Run token counting

```bash
pip3 install -r requirements.txt
python3 scripts/count_tokens.py --encoding o200k_base
```

Writes `results/current.{md,json,csv}` and prints the markdown table to stdout.

## Perplexity baseline

`scripts/score_perplexity.py` scores each reference implementation under a small local code LM and reports `total_bits` per row and `bpb` for cross-task aggregation. The Metrics section above defines the formulas. `--model PATH` is required; the canonical baseline scorer is base Qwen2.5-Coder-3B Q5_K_M (see below).

The canonical scorer is the **base** Qwen2.5-Coder-3B, NOT the `-Instruct` variant. Instruct-tuned models bias probability mass toward markdown code fences and explanatory prose, inflating bits on bare code.

### Install

The perplexity dependency is in the same `requirements.txt` as `tiktoken`, so the install line above already covers it. For a meaningful CPU speedup on long-running scoring, rebuild llama-cpp-python with a tuned BLAS backend for your platform:

```bash
# Apple Silicon (GPU via Metal, 5-10x faster)
CMAKE_ARGS="-DGGML_METAL=on" pip3 install --force-reinstall --no-binary llama-cpp-python llama-cpp-python

# Intel/AMD Mac (Apple Accelerate BLAS, 30-50% faster matmul)
CMAKE_ARGS="-DGGML_BLAS=on -DGGML_BLAS_VENDOR=Apple" pip3 install --force-reinstall --no-binary llama-cpp-python llama-cpp-python

# Linux (OpenBLAS, similar matmul speedup; install libopenblas-dev/openblas-devel first)
CMAKE_ARGS="-DGGML_BLAS=on -DGGML_BLAS_VENDOR=OpenBLAS" pip3 install --force-reinstall --no-binary llama-cpp-python llama-cpp-python
```

On Linux the pip install often compiles from source and needs OpenMP development headers:

```bash
sudo apt install libomp-dev      # Debian/Ubuntu
sudo dnf install libomp-devel    # Fedora/RHEL
```

### Download the canonical scorer model

```bash
scripts/download_scorer_model.sh
```

Default downloads Qwen2.5-Coder-3B Q5_K_M (~2.1 GB, the **base** variant) to `models/` (gitignored). Pass a preset (e.g. `qwen-coder-7b`, `qwen-coder-0.5b`) or a full HuggingFace spec to override; run `scripts/download_scorer_model.sh --help` for the list. Any GGUF works via `--model PATH`, but the baseline snapshot was scored against this specific quant.

### Run

```bash
python3 scripts/score_perplexity.py --model models/qwen2.5-coder-3b-q5_k_m.gguf
```

One invocation writes `results/current_perplexity.{md,json,csv}` and prints the markdown table to stdout (mirrors `count_tokens.py`). The committed snapshot lives at `results/baseline_perplexity.{md,json}` (rendered numbers are in the "Perplexity baseline table" section above).
