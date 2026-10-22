#!/usr/bin/env bash
set -uo pipefail

# Verify de book-scraper: pytest offline con fixtures (sin red). Deja recibo en .agent/last-verify.txt.

cd "$(dirname "$0")/.."
mkdir -p .agent

out=$( { uv run --locked pytest -q; } 2>&1 )
code=$?

printf '%s\n' "$out"

stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
head_="$(git rev-parse HEAD 2>/dev/null || echo sin-git)"
dirty_="$(git diff HEAD 2>/dev/null | sha256sum | cut -c1-12)"
printf '%s exit=%s HEAD=%s dirty-diff=%s\n' "$stamp" "$code" "$head_" "$dirty_" > .agent/last-verify.txt

if [ "$code" -eq 0 ]; then
  echo "VERIFY OK"
else
  echo "VERIFY FAILED (exit $code)"
fi
exit "$code"
