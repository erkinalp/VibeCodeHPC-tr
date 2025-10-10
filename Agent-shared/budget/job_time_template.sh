#!/bin/bash
# ジョブScript用時刻Kayıtテンプレート
# PGは自分のジョブScriptの先頭と末尾にこれを追加

# === ジョブBaşlangıç時（Script先頭に追加） ===
JOB_START=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
JOB_START_EPOCH=$(date -u +%s)
echo "=== JOB STARTED ==="
echo "START_TIME: $JOB_START"
echo "JOB_ID: ${SLURM_JOB_ID:-${PBS_JOBID:-${PJM_JOBID:-UNKNOWN}}}"
echo "RESOURCE_GROUP: ${RESOURCE_GROUP:-cx-small}"  # PGが事前に設定

# === 実際のİşleme ===
# ./your_program

# === ジョブSonlandırma時（Script末尾に追加） ===
JOB_END=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
JOB_END_EPOCH=$(date -u +%s)
RUNTIME_SEC=$((JOB_END_EPOCH - JOB_START_EPOCH))

echo "=== JOB FINISHED ==="
echo "END_TIME: $JOB_END"
echo "RUNTIME_SEC: $RUNTIME_SEC"

# ChangeLog.md更新用の情報を出力
echo ""
echo "# ChangeLog.md更新用（コピペ用）"
echo "    - start_time: \`$JOB_START\`"
echo "    - end_time: \`$JOB_END\`"
echo "    - runtime_sec: \`$RUNTIME_SEC\`"