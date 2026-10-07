#!/usr/bin/env bash
# Keep every published copy of the site in step with the data and with each
# other.
#
# WHY TWO COPIES EXIST
#   GitHub Pages for this repository is configured (by whoever set it up, via
#   the repo settings) to publish from the repository ROOT, and that setting
#   cannot be changed with the available token. The canonical, reviewable site
#   therefore lives in docs/, and root-level copies are generated from it.
#
#   No path rewriting is needed: app.js resolves its data files by trying the
#   root layout first and falling back to the docs layout (see loadFirst()).
#
# tests/test_pipeline.py::TestSiteDataContract asserts these copies stay
# byte-identical, so forgetting to run this fails the test suite rather than
# silently shipping a stale page.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

mkdir -p "$root/docs/data"

# 1. data artefacts -> docs/data (docs layout)
cp "$root/data/discrepancies.json"                  "$root/docs/data/"
cp "$root/data/evidence/score_integrity_study.json" "$root/docs/data/"
cp "$root/data/market_sensitivity_2025_2026.json"   "$root/docs/data/"

# 1b. the live detection feed and monitor-health state -> docs/data/alerts/
#     (optional: a fresh fork has no runs yet, and the site renders
#     "no runs recorded" / "no attempt recorded" rather than breaking)
mkdir -p "$root/docs/data/alerts"
if [ -f "$root/data/alerts/feed.json" ]; then
  cp "$root/data/alerts/feed.json" "$root/docs/data/alerts/"
fi
if [ -f "$root/data/alerts/health.json" ]; then
  cp "$root/data/alerts/health.json" "$root/docs/data/alerts/"
fi

# 2. canonical site assets -> repository root (root layout)
for f in index.html app.js styles.css; do
  cp "$root/docs/$f" "$root/$f"
done
cp "$root/docs/.nojekyll" "$root/.nojekyll"

echo "synced 4 data artefacts + optional live feed -> docs/data/ and 4 site assets -> repo root"
