#!/bin/bash
# Batch Runner — Run with proxy rotation and retry logic
# Usage: ./batch_runner.sh [num_accounts] [proxy_list_file]

set -e

NUM_ACCOUNTS=${1:-5}
PROXY_FILE=${2:-""}
OUTPUT="results_$(date +%Y%m%d_%H%M%S).json"

echo "☁️  Batch Runner — Creating $NUM_ACCOUNTS accounts"

if [ -n "$PROXY_FILE" ] && [ -f "$PROXY_FILE" ]; then
    echo "📡 Using proxy rotation from: $PROXY_FILE"
    PROXIES=($(cat "$PROXY_FILE" | grep -v '^#' | tr '\n' ' '))
    PROXY_COUNT=${#PROXIES[@]}
    echo "  Found $PROXY_COUNT proxies"

    for i in $(seq 1 $NUM_ACCOUNTS); do
        PROXY_IDX=$(( (i - 1) % PROXY_COUNT ))
        PROXY="${PROXIES[$PROXY_IDX]}"
        echo ""
        echo "━━━ Account $i/$NUM_ACCOUNTS (proxy: ${PROXY:0:30}...) ━━━"
        xvfb-run --auto-servernum python main.py \
            --accounts 1 \
            --proxy "$PROXY" \
            --output "$OUTPUT" \
            --delay 60 || true
    done
else
    echo "📡 No proxy file — using direct connection"
    xvfb-run --auto-servernum python main.py \
        --accounts "$NUM_ACCOUNTS" \
        --output "$OUTPUT" \
        --delay 300
fi

echo ""
echo "📊 Results saved to: $OUTPUT"
python3 -c "
import json
with open('$OUTPUT') as f:
    data = json.load(f)
full = sum(1 for r in data if r.get('status') == 'full')
signup = sum(1 for r in data if r.get('status') == 'signup_only')
err = sum(1 for r in data if r.get('status') == 'error')
print(f'  Full (with token): {full}')
print(f'  Signup only:       {signup}')
print(f'  Errors:            {err}')
"
