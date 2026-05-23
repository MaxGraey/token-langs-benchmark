#!/usr/bin/env bash
# Download a perplexity-scorer model from HuggingFace.
#
# Usage:
#   scripts/download_scorer_model.sh [model] [-o target]
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
URL="https://huggingface.co/${REPO}/resolve/main/${FILE}"

if [[ -s "$TARGET" ]]; then
    echo "already exists: $TARGET"
    exit 0
fi

mkdir -p "$(dirname "$TARGET")"

AUTH=()
if [[ -n "${HF_TOKEN:-}" ]]; then
    AUTH=(-H "Authorization: Bearer $HF_TOKEN")
fi

echo "downloading $URL"
echo "         -> $TARGET"
if [[ -s "$PARTIAL" ]]; then
    echo "resuming from partial: $(human "$(filesize "$PARTIAL")")"
fi
echo

# Walk the redirect chain via HEAD; the FINAL response carries the real
# content-length (LFS redirects en-route each have their own short bodies).
total=$(curl -sIL ${AUTH[@]+"${AUTH[@]}"} "$URL" | awk -F': ' '
    tolower($1) == "content-length" { gsub(/\r/, "", $2); val = $2 }
    END { print val }')
total=${total:-0}

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
    printf '\n  error: download failed (exit %d). Partial kept at %s; re-run to resume.\n' "$?" "$PARTIAL" >&2
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
