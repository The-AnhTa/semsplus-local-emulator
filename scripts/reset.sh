#!/usr/bin/env sh
set -eu

BASE_URL="${1:-http://localhost:8080}"
curl --fail --silent --show-error -X POST "$BASE_URL/api/admin/reset"
printf '\n'

