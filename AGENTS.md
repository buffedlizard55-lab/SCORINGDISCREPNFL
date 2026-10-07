# Start here every session
Read README.md in full, then docs/RESEARCH.md and docs/REVIEW.md before making changes.
The README investigation brief and Core Values are the project acceptance criteria.
Never invent evidence, dates, original values, offered lines, or settlement results.
Keep provider-detected candidates separate from confirmed NFL corrections. Unknown is not zero.
Run tests and the three-pass review. Update limitations and next actions honestly.
The raw corrections layer is GENERATED. Never hand-edit data/verified_corrections_raw.json;
add the archived page to data/evidence/pages/ and run pipeline/ingest_rendered.py --write.
record_id is content-derived (SC-<10 hex>) and stable under insertion; record_ordinal is
the positional one. In prose prefer the natural key season|week|player|stat|correction_date.
Never conflate a run's identical_inputs (the compared frozen-field projection) with
source_file_changed (the whole upstream file): the manifests prove they differ.
After changing docs/ run ./pipeline/sync_site_data.sh, then python3 -m unittest discover -s tests.
Order matters at the end of any session: run.py atom -> run.py health -> sync_site_data.sh,
because health.json and the Atom feeds are generated artefacts and a stale copy fails the suite.
Never hand-write data/alerts/health.json, data/alerts/attempts.json, data/alerts/feed.atom,
data/corrections.atom or data/evidence/upstream_churn_study.json; regenerate them
(health, `run.py attempt`, atom, churn).
data/alerts/attempts.json is the ATTEMPT ledger (did a scheduled run happen, ok/baseline/
failed); data/alerts/health.json is the monitor SELF-ASSESSMENT (eight checks) and reads
the ledger. They are different artefacts with different writers - do not merge them by hand.
A test asserts the published health report matches a fresh assessment of the repo, so an
un-synced run fails the build rather than shipping a stale "healthy" badge.
New evidence from the archive goes through pipeline/verify_artefact.py before it is trusted:
a row count that disagrees with its page is a build failure, not a footnote.

