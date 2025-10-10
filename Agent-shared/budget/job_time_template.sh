#!/bin/bash

JOB_START=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
JOB_START_EPOCH=$(date -u +%s)
echo "=== JOB STARTED ==="
echo "START_TIME: $JOB_START"
echo "JOB_ID: ${SLURM_JOB_ID:-${PBS_JOBID:-${PJM_JOBID:-UNKNOWN}}}"
echo "RESOURCE_GROUP: ${RESOURCE_GROUP:-cx-small}"  # PG önceden ayarlar

# ./your_program

JOB_END=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
JOB_END_EPOCH=$(date -u +%s)
RUNTIME_SEC=$((JOB_END_EPOCH - JOB_START_EPOCH))

echo "=== JOB FINISHED ==="
echo "END_TIME: $JOB_END"
echo "RUNTIME_SEC: $RUNTIME_SEC"

# ChangeLog.md güncellemesi için bilgileri yazdır
echo ""
echo "# ChangeLog.md güncellemesi için (kopyala-yapıştır)"
echo "    - start_time: \`$JOB_START\`"
echo "    - end_time: \`$JOB_END\`"
echo "    - runtime_sec: \`$RUNTIME_SEC\`"
