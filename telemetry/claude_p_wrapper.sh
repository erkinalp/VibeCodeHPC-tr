#!/bin/bash
# claude -p Komutのラッパー（統計収集用）
# Ajanが claude -p をKullanımする際の統計をKayıt

# Ortam değişkeniからAjanIDを取得
CALLING_AGENT="${AGENT_ID:-unknown}"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Projeルートの取得
if [ -n "$VIBECODE_ROOT" ]; then
    PROJECT_ROOT="$VIBECODE_ROOT"
else
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
fi

LOG_DIR="$PROJECT_ROOT/telemetry/sub_agent"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/sub_agent_usage.jsonl"

# Argümanチェック
if [ $# -lt 1 ]; then
    echo "Usage: $0 <query>"
    echo "This is a wrapper for 'claude -p' that tracks usage statistics"
    exit 1
fi

QUERY="$1"

# クエリ内のDosyaYolを検出（簡易版）
FILES_REFERENCED=""
if echo "$QUERY" | grep -qE '\.(md|txt|py|c|cpp|h|sh|json|yaml)'; then
    # Dosya名を含む可能性がある
    FILES_REFERENCED=$(echo "$QUERY" | grep -oE '[A-Za-z0-9_\-./]+\.[A-Za-z0-9]+' | tr '\n' ',' | sed 's/,$//')
fi

# Başlangıç時刻をKayıt
START_TIME=$(date +%s.%N)

# claude -p をYürütme（出力をキャプチャ）
OUTPUT_FILE="$LOG_DIR/.temp_output_$$"
claude -p "$QUERY" > "$OUTPUT_FILE" 2>&1
EXIT_CODE=$?

# Sonlandırma時刻をKayıt
END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc)

# 出力を表示
cat "$OUTPUT_FILE"

# 出力サイズを計算（トークン数の簡易推定：4文字=1トークン）
OUTPUT_SIZE=$(wc -c < "$OUTPUT_FILE")
OUTPUT_TOKENS=$((OUTPUT_SIZE / 4))

# 入力サイズを推定（クエリ＋参照Dosyaのサイズ）
INPUT_SIZE=${#QUERY}
INPUT_TOKENS=$((INPUT_SIZE / 4))

# 参照Dosyaのサイズを追加
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

# 圧縮率を計算
if [ $INPUT_TOKENS -gt 0 ]; then
    COMPRESSION_RATIO=$(echo "scale=2; $OUTPUT_TOKENS / $INPUT_TOKENS" | bc)
else
    COMPRESSION_RATIO="1.00"
fi

# JSONレコードを作成
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

# GünlükDosyaに追記
echo "$JSON_RECORD" >> "$LOG_FILE"

# 一時Dosyaを削除
rm -f "$OUTPUT_FILE"

# 元のKomutのSonlandırmaコードを返す
exit $EXIT_CODE