#!/usr/bin/env bash
# clone_repos.sh — Clone all 5 ZoomRx repositories for DTSA code investigation
#
# Usage:
#   bash clone_repos.sh [TARGET_DIR]
#
# TARGET_DIR defaults to ~/zoomrx-repos if not specified.
# After cloning, set DTSA_LOCAL_REPOS_BASE in your .env to the target directory.
#
# Requirements:
#   - git must be installed
#   - Access to phab.zoomrx.com (Phabricator) for 4 of the 5 repos
#   - Access to github.com/ZoomRx for perxcept-ap-server
#
# Phabricator access: you need an account on phab.zoomrx.com and SSH or HTTP
# credentials configured. If cloning fails with a 403/auth error, ask your
# team lead to grant you repository access in Phabricator.

set -e

TARGET_DIR="${1:-$HOME/zoomrx-repos}"

echo "Cloning ZoomRx repositories into: $TARGET_DIR"
echo ""

mkdir -p "$TARGET_DIR"

# ── Phabricator-hosted repos ──────────────────────────────────────────────────
PHAB_BASE="http://phab.zoomrx.com/source"

clone_or_pull() {
  local name="$1"
  local url="$2"
  local dest="$TARGET_DIR/$name"

  if [ -d "$dest/.git" ]; then
    echo "  ↻ $name already exists — pulling latest..."
    git -C "$dest" pull --ff-only
  else
    echo "  ↓ Cloning $name..."
    git clone "$url" "$dest"
  fi
}

clone_or_pull "digitrace-chrome-extension"       "$PHAB_BASE/digitrace-chrome-extension.git"
clone_or_pull "perxcept-ios"                     "$PHAB_BASE/perxcept-ios.git"
clone_or_pull "perxcept-macos"                   "$PHAB_BASE/perxcept-macos.git"
clone_or_pull "perxcept-data-processing-service" "$PHAB_BASE/perxcept-data-processing-service.git"

# ── GitHub-hosted repo ────────────────────────────────────────────────────────
clone_or_pull "perxcept-ap-server" "https://github.com/ZoomRx/perxcept-ap-server.git"

echo ""
echo "Done. Add this line to your .env:"
echo ""
echo "  DTSA_LOCAL_REPOS_BASE=$TARGET_DIR"
echo ""
