#!/usr/bin/env bash
# Download a perplexity-scorer model from HuggingFace.
#
# Usage:
#   scripts/download_model.sh [model] [-o target]
#
# `model` is a preset name (see below) or a full HF spec in REPO/FILE form
# where REPO may contain slashes (e.g. Qwen/Qwen2.5-Coder-7B-GGUF) and FILE
# is the GGUF filename within that repo. Defaults to qwen-coder-3b.
#
# `target` defaults to <repo-root>/models/<filename>. Resumes interrupted
# downloads via a .part file. Set HF_TOKEN if anonymous downloads return 401.

set -euo pipefail

PRESETS=(
    "qwen-coder-0.5b:Qwen/Qwen2.5-Coder-0.5B-GGUF:qwen2.5-coder-0.5b-q5_k_m.gguf"
    "qwen-coder-1.5b:Qwen/Qwen2.5-Coder-1.5B-GGUF:qwen2.5-coder-1.5b-q5_k_m.gguf"
    "qwen-coder-3b:Qwen/Qwen2.5-Coder-3B-GGUF:qwen2.5-coder-3b-q5_k_m.gguf"
    "qwen-coder-7b:Qwen/Qwen2.5-Coder-7B-GGUF:qwen2.5-coder-7b-q5_k_m.gguf"
    "qwen-coder-14b:Qwen/Qwen2.5-Coder-14B-GGUF:qwen2.5-coder-14b-q5_k_m.gguf"
)

# Ollama registry tags mapped from each preset; used as auto-fallback when
# anonymous HF is blocked (some CloudFront PoPs return 401 without HF_TOKEN).
# Ollama registry is anonymous and serves identical GGUF blobs.
OLLAMA_TAGS=(
    "qwen-coder-0.5b:qwen2.5-coder:0.5b-base-q5_K_M"
    "qwen-coder-1.5b:qwen2.5-coder:1.5b-base-q5_K_M"
    "qwen-coder-3b:qwen2.5-coder:3b-base-q5_K_M"
    "qwen-coder-7b:qwen2.5-coder:7b-base-q5_K_M"
    "qwen-coder-14b:qwen2.5-coder:14b-base-q5_K_M"
)

DEFAULT_PRESET="qwen-coder-3b"

usage() {
    sed -n '2,13s/^# \{0,1\}//p' "$0"
    echo
    echo "Presets:"
    for entry in "${PRESETS[@]}"; do
        echo "  ${entry%%:*}"
    done
}

filesize() {
    stat -f%z "$1" 2>/dev/null || stat -c%s "$1" 2>/dev/null || echo 0
}

human() {
    awk -v b="$1" 'BEGIN {
        if (b >= 1073741824)   printf "%.2f GB", b/1073741824
        else if (b >= 1048576) printf "%.1f MB", b/1048576
        else if (b >= 1024)    printf "%.1f KB", b/1024
        else                   printf "%d B",   b
    }'
}

draw_bar() {
    local current=$1 total=$2 width=40
    local pct=0 filled=0
    if (( total > 0 )); then
        pct=$(( current * 100 / total ))
        if (( pct > 100 )); then pct=100; fi
        filled=$(( current * width / total ))
        if (( filled > width )); then filled=$width; fi
    fi
    local bar=""
    local i
    for ((i = 0; i < filled; i++)); do bar+="="; done
    if (( filled < width )) && (( current > 0 )); then
        bar+=">"
        for ((i = filled + 1; i < width; i++)); do bar+=" "; done
    else
        for ((i = filled; i < width; i++)); do bar+=" "; done
    fi
    printf '\r  [%s] %3d%%  %s / %s   ' "$bar" "$pct" "$(human "$current")" "$(human "$total")"
}

MODEL=""
TARGET=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)    usage; exit 0 ;;
        -o|--output)  TARGET="$2"; shift 2 ;;
        -*)           echo "unknown flag: $1" >&2; usage >&2; exit 2 ;;
        *)            MODEL="$1"; shift ;;
    esac
done

MODEL="${MODEL:-$DEFAULT_PRESET}"

REPO=""
FILE=""
for entry in "${PRESETS[@]}"; do
    if [[ "${entry%%:*}" == "$MODEL" ]]; then
        rest="${entry#*:}"
        REPO="${rest%:*}"
        FILE="${rest#*:}"
        break
    fi
done

if [[ -z "$REPO" ]]; then
    if [[ "$MODEL" == */*/* ]]; then
        FILE="${MODEL##*/}"
        REPO="${MODEL%/*}"
    else
        echo "unknown preset: $MODEL" >&2
        usage >&2
        exit 2
    fi
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
TARGET="${TARGET:-$REPO_ROOT/models/$FILE}"
PARTIAL="$TARGET.part"
HF_URL="https://huggingface.co/${REPO}/resolve/main/${FILE}"

OLLAMA_TAG=""
for entry in "${OLLAMA_TAGS[@]}"; do
    if [[ "${entry%%:*}" == "$MODEL" ]]; then
        OLLAMA_TAG="${entry#*:}"
        break
    fi
done

if [[ -s "$TARGET" ]]; then
    echo "already exists: $TARGET"
    exit 0
fi

mkdir -p "$(dirname "$TARGET")"

AUTH=()
if [[ -n "${HF_TOKEN:-}" ]]; then
    AUTH=(-H "Authorization: Bearer $HF_TOKEN")
fi

echo "trying HuggingFace: $HF_URL"

# Preflight: walk the redirect chain via HEAD. On non-200 from HF, fall back
# to the Ollama registry (anonymous, same GGUF bytes) when a preset has one.
head_status=$(curl -sIL ${AUTH[@]+"${AUTH[@]}"} -o /tmp/_dl_head.$$ -w '%{http_code}' "$HF_URL")
total=$(awk -F': ' '
    tolower($1) == "content-length" { gsub(/\r/, "", $2); val = $2 }
    END { print val }' /tmp/_dl_head.$$)
rm -f /tmp/_dl_head.$$
total=${total:-0}

if [[ "$head_status" == "200" ]]; then
    URL="$HF_URL"
    echo "  HF OK ($(human "$total"))"
elif [[ -n "$OLLAMA_TAG" ]]; then
    echo "  HF returned HTTP $head_status; falling back to Ollama registry..."
    OLLAMA_REPO="${OLLAMA_TAG%%:*}"
    OLLAMA_VAR="${OLLAMA_TAG#*:}"
    manifest=$(curl -sf "https://registry.ollama.ai/v2/library/${OLLAMA_REPO}/manifests/${OLLAMA_VAR}" || true)
    result=$(printf '%s' "$manifest" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    for layer in d.get("layers", []):
        if layer.get("mediaType") == "application/vnd.ollama.image.model":
            print(layer["digest"], layer["size"])
            sys.exit(0)
except Exception:
    pass
sys.exit(1)
' 2>/dev/null || true)
    if [[ -z "$result" ]]; then
        echo "error: Ollama manifest fetch failed for $OLLAMA_TAG" >&2
        echo "  primary HF source returned HTTP $head_status" >&2
        exit 2
    fi
    digest="${result% *}"
    total="${result#* }"
    URL="https://registry.ollama.ai/v2/library/${OLLAMA_REPO}/blobs/${digest}"
    AUTH=()
    echo "  Ollama OK: $digest ($(human "$total"))"
else
    echo "error: HF returned HTTP $head_status, and no Ollama fallback for this preset" >&2
    if [[ "$head_status" == "401" || "$head_status" == "403" ]] && [[ -z "${HF_TOKEN:-}" ]]; then
        echo "  anonymous downloads from this network appear blocked." >&2
        echo "  get a free read-token at https://huggingface.co/settings/tokens" >&2
        echo "  then retry: HF_TOKEN=hf_xxx $0" >&2
    fi
    exit 2
fi

echo "         -> $TARGET"

# If the leftover partial does not start with GGUF, it is junk (e.g. cached
# 401 body from a previous failed run); remove so resume does not corrupt.
if [[ -s "$PARTIAL" ]]; then
    if [[ "$(head -c 4 "$PARTIAL" 2>/dev/null)" != "GGUF" ]]; then
        echo "  (discarding non-GGUF partial: $(human "$(filesize "$PARTIAL")"))"
        rm -f "$PARTIAL"
    else
        echo "resuming from partial: $(human "$(filesize "$PARTIAL")")"
    fi
fi
echo

curl --silent --location --fail --continue-at - ${AUTH[@]+"${AUTH[@]}"} --output "$PARTIAL" "$URL" &
pid=$!

trap 'kill "$pid" 2>/dev/null; echo; echo "interrupted; partial download kept at $PARTIAL"; exit 130' INT TERM

if [[ -t 2 ]]; then
    while kill -0 "$pid" 2>/dev/null; do
        draw_bar "$(filesize "$PARTIAL")" "$total"
        sleep 0.3
    done
fi

if wait "$pid"; then
    if [[ -t 2 ]]; then
        draw_bar "$(filesize "$PARTIAL")" "$total"
        printf '\n'
    fi
else
    rc=$?
    # If partial is junk (no GGUF magic), discard so the next run starts fresh.
    if [[ -s "$PARTIAL" ]] && [[ "$(head -c 4 "$PARTIAL" 2>/dev/null)" != "GGUF" ]]; then
        rm -f "$PARTIAL"
        printf '\n  error: download failed (exit %d); partial was junk and was removed.\n' "$rc" >&2
    else
        printf '\n  error: download failed (exit %d). Partial kept at %s; re-run to resume.\n' "$rc" "$PARTIAL" >&2
    fi
    if [[ -z "${HF_TOKEN:-}" ]]; then
        echo "  if HF returned 401, set HF_TOKEN and retry." >&2
    fi
    exit 1
fi

magic="$(head -c 4 "$PARTIAL" 2>/dev/null || true)"
if [[ "$magic" != "GGUF" ]]; then
    echo "error: downloaded file does not look like GGUF (HF returned an error page?)" >&2
    rm -f "$PARTIAL"
    exit 1
fi

mv "$PARTIAL" "$TARGET" || {
    echo "error: rename failed: $PARTIAL -> $TARGET" >&2
    exit 1
}

echo "done: $TARGET"
