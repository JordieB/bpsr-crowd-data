#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://127.0.0.1:8000}
API_KEY=${SMOKE_API_KEY:-smoke-test-key}

payload=$(cat <<JSON
{
  "source": "manual",
  "category": "boss_event",
  "region": "NA",
  "boss_name": "Shell Smoke",
  "payload": {"note": "shell smoke"}
}
JSON
)

id=$(curl -s -X POST "$BASE_URL/v1/ingest" -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" -d "$payload" | jq -r '.id')
if [[ "$id" == "null" || -z "$id" ]]; then
  echo "Failed to ingest payload" >&2
  exit 1
fi

recent=$(curl -s "$BASE_URL/v1/submissions/recent?category=boss_event&limit=1" | jq -r '.[0].id')
if [[ "$recent" != "$id" ]]; then
  echo "Smoke check failed" >&2
  exit 1
fi

echo "SMOKE SH OK"
