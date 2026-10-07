#!/usr/bin/env bash
# Copy the source-of-truth artefacts into docs/data/ so the published site can
# never drift from the data it claims to describe.
#
# tests/test_pipeline.py::TestSiteDataContract asserts these copies stay
# byte-identical, so forgetting to run this makes the test suite fail rather
# than silently shipping a stale page.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$root/docs/data"
cp "$root/data/discrepancies.json"                       "$root/docs/data/"
cp "$root/data/evidence/score_integrity_study.json"      "$root/docs/data/"
cp "$root/data/market_sensitivity_2025_2026.json"        "$root/docs/data/"
echo "synced 3 artefacts -> docs/data/"
