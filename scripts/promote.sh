#!/usr/bin/env bash
# Promote current main to PROD by cutting a version tag (triggers cd.yml).
set -euo pipefail

VERSION="${1:-}"
[ -n "$VERSION" ] || { echo "usage: scripts/promote.sh v0.1.0"; exit 1; }
[[ "$VERSION" == v* ]] || { echo "version must start with 'v'"; exit 1; }

git fetch origin main
git checkout main
git pull --ff-only origin main

echo "==> Tagging $VERSION at $(git rev-parse --short HEAD)"
git tag -a "$VERSION" -m "release $VERSION"
git push origin "$VERSION"

echo "==> Pushed. GitHub Actions will deploy to PROD. Watch: gh run watch"
