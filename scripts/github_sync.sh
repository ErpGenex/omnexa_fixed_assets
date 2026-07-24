#!/usr/bin/env bash
# Safe GitHub sync for this app.
# Usage:
#   ./scripts/github_sync.sh
#   ./scripts/github_sync.sh "Custom commit message"
#
# Behavior:
# - stages every change with git add -A (including deletions/renames)
# - commits only when there are staged changes
# - pushes the current branch to origin
set -euo pipefail

APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_ROOT"

branch="$(git branch --show-current)"
if [[ -z "$branch" ]]; then
  echo "ERROR: detached HEAD; checkout a branch before syncing."
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  if [[ -n "${GITHUB_REMOTE_URL:-}" ]]; then
    git remote add origin "$GITHUB_REMOTE_URL"
  elif [[ -n "${GITHUB_ORG:-}" ]]; then
    repo_name="$(basename "$APP_ROOT")"
    if [[ "${GITHUB_REMOTE_STYLE:-ssh}" == "https" ]]; then
      git remote add origin "https://github.com/${GITHUB_ORG}/${repo_name}.git"
    else
      git remote add origin "git@github.com:${GITHUB_ORG}/${repo_name}.git"
    fi
  else
    echo "ERROR: origin remote is missing. Set GITHUB_REMOTE_URL or GITHUB_ORG."
    exit 1
  fi
fi

git add -A
if git diff --cached --quiet; then
  echo "No changes to commit."
else
  msg="${1:-Update code}"
  git commit -m "$msg"
fi

git push -u origin "$branch"
echo "Synced $branch to origin without dropping tracked changes."
