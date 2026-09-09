#!/usr/bin/env bash
# scripts/provision.sh — what a fresh worktree of THIS repo needs. wt.sh runs it
# from the new worktree's root.
#
# The heavy dependency is the yeaboi wheel itself: this repo asserts against
# what ships, not against a source tree.

set -euo pipefail

UV="$(command -v uv 2>/dev/null || echo "$HOME/.local/bin/uv")"
"$UV" sync --all-extras --quiet
echo "[provision] harness ready — 'make test' is hermetic, 'make up' needs AWS"
