#!/bin/bash

CALLING_AGENT="${AGENT_ID:-unknown}"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

if [ -n "$VIBECODE_ROOT" ]; then
    PROJECT_ROOT="$VIBECODE_ROOT"
else
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
fi

LOG_DIR="$PROJECT_ROOT/telemetry/sub_agent"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/sub_agent_usage.jsonl"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <query>"
    echo "This is a wrapper for 'claude -p' that tracks usage statistics"
    exit 1
fi

QUERY="$1"

FILES_REFERENCED=""
if echo "$QUERY" | grep -qE '\.(md|txt|py|c|cpp|h|sh|json|yaml)'; then
    FILES_REFERENCED=$(echo "$QUERY" | grep -oE '[A-Za-z0-9_\-./]+\.[A-Za-z0-9]+' | tr '\n' ',' | sed 's/,$//')
fi

START_TIME=$(date +%s.%N)

OUTPUT_FILE="$LOG_DIR/.temp_output_$$"
claude -p "$QUERY" > "$OUTPUT_FILE" 2>&1
EXIT_CODE=$?

END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc)

cat "$OUTPUT_FILE"

OUTPUT_SIZE=$(wc -c < "$OUTPUT_FILE")
OUTPUT_TOKENS=$((OUTPUT_SIZE / 4))

INPUT_SIZE=${#QUERY}
INPUT_TOKENS=$((INPUT_SIZE / 4))

if [ -n "$FILES_REFERENCED" ]; then
    IFS=',' read -ra FILE_ARRAY <<< "$FILES_REFERENCED"
    for file in "${FILE_ARRAY[@]}"; do
        if [ -f "$PROJECT_ROOT/$file" ]; then
            FILE_SIZE=$(wc -c < "$PROJECT_ROOT/$file" 2>/dev/null || echo 0)
            INPUT_SIZE=$((INPUT_SIZE + FILE_SIZE))
        fi
    done
    INPUT_TOKENS=$((INPUT_SIZE / 4))
fi

if [ $INPUT_TOKENS -gt 0 ]; then
    COMPRESSION_RATIO=$(echo "scale=2; $OUTPUT_TOKENS / $INPUT_TOKENS" | bc)
else
    COMPRESSION_RATIO="1.00"
fi

JSON_RECORD=$(cat <<EOF
{
  "timestamp": "$TIMESTAMP",
  "calling_agent": "$CALLING_AGENT",
  "query_length": ${#QUERY},
  "files_referenced": "$FILES_REFERENCED",
  "input_tokens_estimated": $INPUT_TOKENS,
  "output_tokens_estimated": $OUTPUT_TOKENS,
  "compression_ratio": $COMPRESSION_RATIO,
  "duration_seconds": $DURATION,
  "success": $([ $EXIT_CODE -eq 0 ] && echo "true" || echo "false"),
  "exit_code": $EXIT_CODE
}
EOF
)

echo "$JSON_RECORD" >> "$LOG_FILE"

rm -f "$OUTPUT_FILE"

exit $EXIT_CODE
