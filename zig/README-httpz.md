The `src/http_rest.zig` file is counted as source for the HTTP REST benchmark.
It uses the common `httpz`-style API shape. Because Zig package metadata changes
frequently, wire the exact current `httpz` dependency in `build.zig.zon` before
running it locally.
