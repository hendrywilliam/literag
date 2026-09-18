#!/usr/bin/env sh
# Load test runner.
#
# Loads loadtest/.env when present, applies KEY=VALUE overrides from the command
# line, then runs k6 against loadtest/main.js.
#
# Examples:
#   ./loadtest/run.sh SCENARIO=smoke
#   ./loadtest/run.sh SCENARIO=read READ_RPS=100
#   ./loadtest/run.sh SCENARIO=write ALLOW_DESTRUCTIVE=true \
#     DELETE_DOCUMENT_IDS=doc-1 DELETE_CHUNK_IDS=chunk-1

set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ -f "$DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$DIR/.env"
  set +a
fi

for pair in "$@"; do
  case "$pair" in
    *=*)
      key=${pair%%=*}
      value=${pair#*=}
      export "$key"="$value"
      ;;
    *)
      echo "run.sh: expected KEY=VALUE, got '$pair'" >&2
      exit 2
      ;;
  esac
done

K6_BIN=${K6:-k6}
if ! command -v "$K6_BIN" >/dev/null 2>&1; then
  echo "k6 not found. Install: https://grafana.com/docs/k6/latest/set-up/install-k6/" >&2
  exit 1
fi

echo "loadtest: scenario=${SCENARIO:-load} base_url=${BASE_URL:-http://localhost:8080}"

if [ -n "${SUMMARY_EXPORT:-}" ]; then
  mkdir -p "$(dirname -- "$SUMMARY_EXPORT")"
  exec "$K6_BIN" run --summary-export="$SUMMARY_EXPORT" "$DIR/main.js"
fi

exec "$K6_BIN" run "$DIR/main.js"
