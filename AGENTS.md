# Start here every session
Read README.md in full, then docs/RESEARCH.md and docs/REVIEW.md before making changes.
The README investigation brief and Core Values are the project acceptance criteria.
Never invent evidence, dates, original values, offered lines, or settlement results.
Keep provider-detected candidates separate from confirmed NFL corrections. Unknown is not zero.
Run tests and the three-pass review. Update limitations and next actions honestly.
The raw corrections layer is GENERATED. Never hand-edit data/verified_corrections_raw.json;
add the archived page to data/evidence/pages/ and run pipeline/ingest_rendered.py --write.
Never key anything on record_id: it is a positional ordinal and shifts when rows are added.
After changing docs/ run ./pipeline/sync_site_data.sh, then python3 -m unittest discover -s tests.

