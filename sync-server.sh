#!/usr/bin/env bash
# sync-server.sh — keep the duplicated MCP server code identical across
# dtaa-agent and dtsa-agent.
#
# The two agent repos each carry a full copy of the server so either can be
# cloned and run standalone. That means edits must be mirrored by hand.
#
# Usage:
#   bash sync-server.sh --check     # report drift, change nothing (exit 1 if drift)
#   bash sync-server.sh             # copy this repo's server files to the sibling
#
# Run --check before committing any change to the files listed below.
#
# mcp_server.py is deliberately NOT synced. dtaa-agent carries a lean server
# (2 read-only SQL tools, lazy imports); dtsa-agent carries the full 9-tool one.
# Syncing it would overwrite one with the other.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="$(basename "$HERE")"

case "$NAME" in
  dtsa-agent) SIBLING="$(dirname "$HERE")/dtaa-agent" ;;
  dtaa-agent) SIBLING="$(dirname "$HERE")/dtsa-agent" ;;
  *) echo "error: expected to run from dtaa-agent or dtsa-agent, got '$NAME'" >&2; exit 2 ;;
esac

if [ ! -d "$SIBLING" ]; then
  echo "error: sibling repo not found at $SIBLING" >&2
  exit 2
fi

FILES=(
  config.py
  dtsa_database.py
  mysql_service.py
  synapse_database.py
  synapse_mysql_service.py
  filesystem_service.py
  github_service.py
  phabricator_service.py
  playwright_service.py
  pyproject.toml
  requirements.txt
  .env.example
)

if [ "${1:-}" = "--check" ]; then
  drift=0
  for f in "${FILES[@]}"; do
    if [ ! -f "$SIBLING/$f" ]; then
      echo "MISSING in $NAME's sibling: $f"
      drift=1
    elif ! diff -q "$HERE/$f" "$SIBLING/$f" >/dev/null 2>&1; then
      echo "DRIFT: $f"
      drift=1
    fi
  done
  if [ "$drift" -eq 0 ]; then
    echo "in sync — all ${#FILES[@]} server files identical with $(basename "$SIBLING")"
  else
    echo ""
    echo "Run 'bash sync-server.sh' from whichever repo has the correct version."
  fi
  exit "$drift"
fi

echo "Copying ${#FILES[@]} server files: $NAME -> $(basename "$SIBLING")"
for f in "${FILES[@]}"; do
  cp "$HERE/$f" "$SIBLING/$f"
  echo "  $f"
done
echo ""
echo "Done. Commit the change in BOTH repos."
