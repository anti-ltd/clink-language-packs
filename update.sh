#!/usr/bin/env bash
set -euo pipefail

# Publish a new immutable language-pack release from the assets in Lexicons/.

repo_dir="$(cd "$(dirname "$0")" && pwd)"
cd "$repo_dir"

branch="$(git branch --show-current)"
if [[ "$branch" != main ]]; then
  echo "Switch to main before publishing language packs." >&2
  exit 1
fi

git add -A
if ! git diff --cached --quiet; then
  git commit -m "Update language packs"
fi

git push origin "HEAD:refs/heads/$branch"

echo "Pushed $branch. Relevant changes on main publish through GitHub Actions; check the workflow for completion."
