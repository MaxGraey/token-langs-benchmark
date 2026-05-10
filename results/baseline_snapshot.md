# Baseline snapshot

This is the snapshot from the original comparison. Re-run `scripts/count_tokens.py`
locally to refresh the exact numbers for the included files and your installed
`tiktoken` version/cache.

| Example | Rust tokens | TypeScript tokens | Zig tokens | Winner |
|---|---:|---:|---:|---|
| find-prime-numbers | 158 | 133 | 266 | TypeScript |
| http-rest | 422 | 171 | 535 | TypeScript |
| json-parser | 963 | 622 | 1021 | TypeScript |
| word-frequency | 150 | 123 | 305 | TypeScript |
| **Total** | **1693** | **1049** | **2127** | **TypeScript** |
