#!/usr/bin/env bash
# Send a fake Alertmanager payload to the agent (no Prometheus needed).
# Usage: ./scripts/send-test-alert.sh [url] [pod-name]
set -euo pipefail
URL="${1:-http://localhost:8000/webhook/alertmanager}"
POD="${2:-faulty-app-crash}"
curl -sS -X POST "$URL" -H 'Content-Type: application/json' \
  ${WEBHOOK_TOKEN:+-H "Authorization: Bearer $WEBHOOK_TOKEN"} \
  -d "{\"status\":\"firing\",\"alerts\":[{\"status\":\"firing\",\"labels\":{\"alertname\":\"PodCrashLooping\",\"namespace\":\"opsagent-demo\",\"pod\":\"$POD\"}}]}"
echo
