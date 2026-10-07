"""
Tests for the notification, health, feed-integrity and fact-layer contract work.

These are the tests that keep the *operational* half of the project honest. The
detector's diff rules are covered in test_pipeline.py; what is covered here is
everything that decides whether a human being actually finds out, and whether
"nothing happened" can be told apart from "nothing was checked".

Design rule applied throughout: each guard is MUTATION-CHECKED. A test that only
asserts the happy path proves nothing about the failure path, so for every
safeguard there is a test that reintroduces the bug and asserts the build fails.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import os
import pathlib
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))

import atom  # noqa: E402
import build_database  # noqa: E402
import detect  # noqa: E402
import feed as feed_mod  # noqa: E402
import health  # noqa: E402
import notify  # noqa: E402
import schema  # noqa: E402

NS = {"a": "http://www.w3.org/2005/Atom"}


def report_with_alerts(n=1, old_sha="a" * 64, new_sha="b" * 64):
    changes = [detect.Change(f"2026_01_AAA_{i}", "home_score", "24", "27") for i in range(n)]
    rep = detect.build_alert_report(changes, "test-source", min_severity=1)
    rep["inputs"] = {"old": {"sha256": old_sha}, "new": {"sha256": new_sha}}
    return rep


class FakeResponse:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestIdempotency(unittest.TestCase):
    def test_same_comparison_produces_the_same_key_even_at_a_different_time(self):
        """The whole point: a re-run must not notify a person twice for one change."""
        a = report_with_alerts()
        b = report_with_alerts()
        b["generated_at"] = "2030-01-01T00:00:00+00:00"
        self.assertEqual(notify.idempotency_key(a), notify.idempotency_key(b))

    def test_a_different_comparison_produces_a_different_key(self):
        self.assertNotEqual(notify.idempotency_key(report_with_alerts(old_sha="a" * 64)),
                            notify.idempotency_key(report_with_alerts(old_sha="c" * 64)))

    def test_a_different_alert_set_produces_a_different_key(self):
        self.assertNotEqual(notify.idempotency_key(report_with_alerts(n=1)),
                            notify.idempotency_key(report_with_alerts(n=2)))

    def test_key_does_not_depend_on_alert_order(self):
        a = report_with_alerts(n=2)
        b = copy.deepcopy(a)
        b["alerts"] = list(reversed(b["alerts"]))
        self.assertEqual(notify.idempotency_key(a), notify.idempotency_key(b))


class TestDeliveryReceipts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = os.path.join(self.tmp.name, "deliveries.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_successful_delivery_is_recorded_with_a_receipt(self):
        with patch.object(detect, "notify_webhook", return_value=(True, "http 200")):
            r = notify.deliver(report_with_alerts(), "https://hooks.slack.com/services/T/B/X", self.log)
        self.assertEqual(r["outcome"], "delivered")
        self.assertEqual(r["channel"], "slack")
        self.assertEqual(r["channel_host"], "hooks.slack.com")
        log = notify.load_log(self.log)
        self.assertEqual(log["summary"]["delivered"], 1)
        self.assertEqual(log["summary"]["dead_letter"], 0)

    def test_the_webhook_url_is_never_written_to_the_log(self):
        url = "https://hooks.slack.com/services/T000/B000/SUPERSECRET"
        with patch.object(detect, "notify_webhook", return_value=(True, "http 200")):
            notify.deliver(report_with_alerts(), url, self.log)
        raw = pathlib.Path(self.log).read_text(encoding="utf-8")
        self.assertNotIn("SUPERSECRET", raw)
        self.assertNotIn(url, raw)
        log = notify.load_log(self.log)
        self.assertEqual(len(log["deliveries"][0]["url_sha256"]), 64)

    def test_a_duplicate_delivery_is_suppressed_not_re_sent(self):
        with patch.object(detect, "notify_webhook", return_value=(True, "http 200")) as post:
            notify.deliver(report_with_alerts(), "https://discord.com/api/webhooks/1/t", self.log)
            second = notify.deliver(report_with_alerts(), "https://discord.com/api/webhooks/1/t", self.log)
        self.assertEqual(second["outcome"], "suppressed_duplicate")
        self.assertEqual(post.call_count, 1, "a suppressed duplicate must not hit the network")

    def test_force_overrides_suppression(self):
        with patch.object(detect, "notify_webhook", return_value=(True, "http 200")) as post:
            notify.deliver(report_with_alerts(), "https://discord.com/api/webhooks/1/t", self.log)
            notify.deliver(report_with_alerts(), "https://discord.com/api/webhooks/1/t",
                           self.log, force=True)
        self.assertEqual(post.call_count, 2)

    def test_transient_failure_is_retried_then_succeeds(self):
        slept = []
        with patch.object(detect, "notify_webhook", side_effect=[(False, "http 500"), (True, "http 200")]), \
             patch.object(notify, "BACKOFF_SECONDS", (0, 0, 0)), \
             patch("time.sleep", side_effect=slept.append):
            r = notify.deliver(report_with_alerts(), "https://hooks.slack.com/services/x", self.log)
        self.assertEqual(r["outcome"], "delivered")
        self.assertEqual(r["attempts"], 2)

    def test_exhausted_retries_become_a_dead_letter(self):
        with patch.object(detect, "notify_webhook", side_effect=OSError("connection refused")), \
             patch.object(notify, "BACKOFF_SECONDS", (0, 0, 0)), \
             patch("time.sleep"):
            r = notify.deliver(report_with_alerts(), "https://hooks.slack.com/services/x",
                               self.log, max_attempts=3)
        self.assertEqual(r["outcome"], "failed")
        self.assertTrue(r["dead_letter"])
        self.assertEqual(r["attempts"], 3)
        self.assertIn("connection refused", r["detail"])
        self.assertEqual(notify.load_log(self.log)["summary"]["dead_letter"], 1)

    def test_a_missing_webhook_is_recorded_as_not_configured(self):
        r = notify.deliver(report_with_alerts(), None, self.log)
        self.assertEqual(r["outcome"], "not_configured")
        self.assertEqual(r["attempts"], 0)

    def test_a_clean_comparison_is_recorded_as_skipped(self):
        clean = detect.build_alert_report([], "test-source")
        clean["inputs"] = {"old": {"sha256": "a" * 64}, "new": {"sha256": "b" * 64}}
        with patch.object(detect, "notify_webhook") as post:
            r = notify.deliver(clean, "https://hooks.slack.com/services/x", self.log)
        self.assertEqual(r["outcome"], "skipped_no_alerts")
        post.assert_not_called()

    def test_the_log_is_capped_so_it_cannot_grow_without_bound(self):
        with patch.object(detect, "notify_webhook", return_value=(True, "http 200")):
            for i in range(notify.MAX_ENTRIES + 25):
                rep = report_with_alerts(old_sha=f"{i:064d}"[:64])
                notify.deliver(rep, "https://hooks.slack.com/services/x", self.log)
        self.assertEqual(len(notify.load_log(self.log)["deliveries"]), notify.MAX_ENTRIES)

    def test_every_outcome_is_a_declared_outcome(self):
        self.assertEqual(
            set(notify.OUTCOMES),
            {"delivered", "failed", "skipped_no_alerts", "suppressed_duplicate", "not_configured"})


class TestTransportShapes(unittest.TestCase):
    def test_discord_and_slack_payload_shapes_are_distinct(self):
        self.assertIn("content", detect.webhook_payload("hi", "https://discord.com/api/webhooks/1/t"))
        self.assertIn("text", detect.webhook_payload("hi", "https://hooks.slack.com/services/x"))
        self.assertIn("text", detect.webhook_payload("hi", "https://example.invalid/hook"))

    def test_post_text_reports_a_non_2xx_as_a_failure(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(500)):
            ok, detail = detect.post_text("hi", "https://hooks.slack.com/services/x")
        self.assertFalse(ok)
        self.assertEqual(detail, "http 500")


class TestHealthAssessment(unittest.TestCase):
    """A monitor that cannot report its own death is not a monitor."""

    NOW = dt.datetime(2026, 10, 7, 21, 0, 0, tzinfo=dt.timezone.utc)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        os.makedirs(os.path.join(self.root, "data", "alerts"))
        os.makedirs(os.path.join(self.root, "docs", "data", "alerts"))
        os.makedirs(os.path.join(self.root, "snapshots", "nfldata_games", "2026-10-07T200000Z"))
        pathlib.Path(self.root, "snapshots", "nfldata_games", "2026-10-07T200000Z",
                     "games.slim.csv.manifest.json").write_text(json.dumps({
                         "source_file_sha256": "f" * 64,
                         "upstream_commit_sha": "c" * 40,
                         "upstream_commit_date": "2026-10-07T19:45:00Z",
                     }))

    def tearDown(self):
        self.tmp.cleanup()

    def write_feed(self, checked_at, identical=True, source_changed=True, runs=1):
        entries = [{
            "checked_at": checked_at, "status": "clean", "alerts_total": 0,
            "records_compared": 7340,
            "old_snapshot": f"snapshots/nfldata_games/{i}/games.slim.csv",
            "new_snapshot": f"snapshots/nfldata_games/{i}b/games.slim.csv",
            "old_sha256": "3" * 64, "new_sha256": "3" * 64,
            "identical_inputs": identical, "source_file_changed": source_changed,
            "new_source": {"source_file_sha256": "f" * 64,
                           "upstream_commit_sha": "c" * 40,
                           "upstream_commit_date": "2026-10-07T19:45:00Z"},
        } for i in range(runs)]
        payload = json.dumps({"meta": feed_mod.META, "runs": entries, "latest": entries[0],
                              "summary": {"runs_recorded": runs}})
        pathlib.Path(self.root, "data", "alerts", "feed.json").write_text(payload)
        # A synced checkout publishes the same bytes under docs/; without this the
        # drift check (correctly) fails every fixture.
        pathlib.Path(self.root, "docs", "data", "alerts", "feed.json").write_text(payload)

    def test_a_fresh_healthy_monitor_is_ok_except_for_opt_in_push(self):
        self.write_feed("2026-10-07T20:30:00+00:00")
        r = health.assess(root=self.root, now=self.NOW)
        by = {c["check"]: c["status"] for c in r["checks"]}
        self.assertEqual(by["freshness"], "ok")
        self.assertEqual(by["source_movement"], "ok")
        self.assertEqual(by["snapshot_store"], "ok")
        # push is opt-in, so its absence is UNKNOWN, never silently ok
        self.assertEqual(by["push_notification"], "unknown")
        self.assertEqual(r["status"], "warn")

    def test_a_stale_monitor_fails_and_says_what_to_do(self):
        self.write_feed("2026-10-01T00:00:00+00:00")
        r = health.assess(root=self.root, now=self.NOW)
        self.assertEqual(r["status"], "fail")
        self.assertTrue(any("stale" in i for i in r["irregularities"]))
        self.assertIn("Actions history", r["next_action"])

    def test_no_feed_at_all_is_unknown_never_ok(self):
        """A checkout that has never produced a comparison must not look healthy."""
        r = health.assess(root=self.root, now=self.NOW)
        by = {c["check"]: c["status"] for c in r["checks"]}
        self.assertEqual(by["comparison_feed"], "unknown")
        self.assertEqual(by["freshness"], "unknown")
        self.assertEqual(r["status"], "unknown")
        self.assertIn("Unknown is not clean", r["headline"])

    def test_a_source_that_never_moves_is_flagged_even_when_the_feed_is_fresh(self):
        """Identical upstream bytes across runs means the fetch may be cached."""
        self.write_feed("2026-10-07T20:30:00+00:00", source_changed=False, runs=3)
        r = health.assess(root=self.root, now=self.NOW)
        self.assertEqual({c["check"]: c["status"] for c in r["checks"]}["source_movement"], "warn")

    def test_identical_projection_with_a_moving_source_is_the_expected_healthy_state(self):
        """MUTATION GUARD for the conflation this project actually shipped once."""
        self.write_feed("2026-10-07T20:30:00+00:00", identical=True, source_changed=True, runs=3)
        r = health.assess(root=self.root, now=self.NOW)
        c = {x["check"]: x for x in r["checks"]}["source_movement"]
        self.assertEqual(c["status"], "ok")
        self.assertIn("frozen-field projection changed in none", c["detail"])

    def test_drift_between_canonical_and_published_copies_fails(self):
        self.write_feed("2026-10-07T20:30:00+00:00")
        pathlib.Path(self.root, "docs", "data", "alerts", "feed.json").write_text("{}")
        r = health.assess(root=self.root, now=self.NOW)
        self.assertEqual({c["check"]: c["status"] for c in r["checks"]}["published_copies"], "fail")
        self.assertIn("sync_site_data.sh", r["next_action"])

    def test_a_dead_lettered_notification_fails_the_assessment(self):
        self.write_feed("2026-10-07T20:30:00+00:00")
        pathlib.Path(self.root, "data", "alerts", "deliveries.json").write_text(json.dumps(
            {"meta": notify.META, "deliveries": [
                {"attempted_at": "2026-10-07T20:31:00Z", "outcome": "failed",
                 "dead_letter": True, "attempts": 3, "idempotency_key": "k"}],
             "summary": notify._summarize([
                 {"attempted_at": "2026-10-07T20:31:00Z", "outcome": "failed", "dead_letter": True}])}))
        r = health.assess(root=self.root, now=self.NOW)
        self.assertEqual(r["status"], "fail")
        self.assertIn("dead-letter", r["next_action"])

    def test_a_malformed_atom_feed_fails_rather_than_breaking_subscribers_silently(self):
        self.write_feed("2026-10-07T20:30:00+00:00")
        pathlib.Path(self.root, "data", "alerts", "feed.atom").write_text("<feed><entry></feed>")
        r = health.assess(root=self.root, now=self.NOW)
        self.assertEqual({c["check"]: c["status"] for c in r["checks"]}["atom_feed"], "fail")

    def test_an_atom_feed_out_of_step_with_the_json_feed_fails(self):
        """A real failure this caught during development: the Atom file was
        generated before the newest comparison was appended."""
        self.write_feed("2026-10-07T20:30:00+00:00", runs=2)
        one_run = {"meta": feed_mod.META,
                   "runs": json.loads(pathlib.Path(self.root, "data", "alerts", "feed.json")
                                      .read_text())["runs"][:1]}
        pathlib.Path(self.root, "data", "alerts", "feed.atom").write_text(
            atom.build_detection_feed(one_run, "https://example.invalid/",
                                      now="2026-10-07T20:30:00Z"))
        r = health.assess(root=self.root, now=self.NOW)
        self.assertEqual({c["check"]: c["status"] for c in r["checks"]}["atom_feed"], "fail")

    def test_a_missing_snapshot_store_fails_because_there_is_nothing_to_diff(self):
        self.write_feed("2026-10-07T20:30:00+00:00")
        for p in pathlib.Path(self.root, "snapshots").rglob("*.manifest.json"):
            p.unlink()
        r = health.assess(root=self.root, now=self.NOW)
        self.assertEqual({c["check"]: c["status"] for c in r["checks"]}["snapshot_store"], "fail")

    def test_a_snapshot_without_a_watermark_is_warn_not_ok(self):
        self.write_feed("2026-10-07T20:30:00+00:00")
        pathlib.Path(self.root, "snapshots", "nfldata_games", "2026-10-07T200000Z",
                     "games.slim.csv.manifest.json").write_text(json.dumps({"source_file_sha256": "f" * 64}))
        r = health.assess(root=self.root, now=self.NOW)
        self.assertEqual({c["check"]: c["status"] for c in r["checks"]}["snapshot_store"], "warn")
        self.assertIsNone(r["source_watermark"]["upstream_commit_sha"])

    def test_no_status_is_ever_reported_that_is_not_declared(self):
        self.write_feed("2026-10-07T20:30:00+00:00")
        r = health.assess(root=self.root, now=self.NOW)
        self.assertIn(r["status"], ("ok", "warn", "fail", "unknown"))
        for c in r["checks"]:
            self.assertIn(c["status"], ("ok", "warn", "fail", "unknown"))

    def test_markdown_renders_every_check_and_the_next_action(self):
        self.write_feed("2026-10-07T20:30:00+00:00")
        md = health.render_markdown(health.assess(root=self.root, now=self.NOW))
        for name in ("comparison_feed", "freshness", "source_movement", "snapshot_store",
                     "push_notification", "published_copies"):
            self.assertIn(name, md)
        self.assertIn("Next action:", md)


class TestShippedHealthArtefact(unittest.TestCase):
    def test_the_published_health_report_is_well_formed_and_honest(self):
        p = pathlib.Path(ROOT, "data", "alerts", "health.json")
        if not p.exists():
            self.skipTest("no health artefact published in this checkout")
        d = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn(d["status"], ("ok", "warn", "fail", "unknown"))
        self.assertTrue(d["checks"])
        self.assertIn("what_it_cannot_see", d["meta"])
        names = [c["check"] for c in d["checks"]]
        for required in ("comparison_feed", "freshness", "source_movement",
                         "snapshot_store", "atom_feed", "published_copies"):
            self.assertIn(required, names)

    def test_the_published_health_report_matches_a_fresh_assessment_of_the_repo(self):
        """Guards against a hand-edited or stale health artefact being published."""
        p = pathlib.Path(ROOT, "data", "alerts", "health.json")
        if not p.exists():
            self.skipTest("no health artefact published in this checkout")
        published = json.loads(p.read_text(encoding="utf-8"))
        fresh = health.assess(root=ROOT)
        self.assertEqual(
            [(c["check"], c["status"]) for c in published["checks"]],
            [(c["check"], c["status"]) for c in fresh["checks"]],
            "the published health report does not match a fresh assessment; re-run "
            "`python3 pipeline/run.py health` and ./pipeline/sync_site_data.sh")


class TestAtomFeeds(unittest.TestCase):
    def test_detection_feed_is_well_formed_with_unique_ids(self):
        feed_json = json.loads(pathlib.Path(ROOT, "data", "alerts", "feed.json").read_text())
        xml_text = atom.build_detection_feed(feed_json, "https://example.invalid/")
        root = ET.fromstring(xml_text)
        entries = root.findall("a:entry", NS)
        self.assertEqual(len(entries), len(feed_json["runs"]))
        ids = [e.findtext("a:id", namespaces=NS) for e in entries]
        self.assertEqual(len(set(ids)), len(ids))

    def test_two_clean_runs_on_identical_inputs_do_not_collide(self):
        """MUTATION GUARD: the first implementation hashed only the input
        SHA-256s, so two clean runs comparing byte-identical snapshots produced
        the same Atom id and readers would mark the newer one as already read."""
        run = {"checked_at": "2026-10-07T18:11:31+00:00", "status": "clean", "alerts_total": 0,
               "records_compared": 7340, "old_sha256": "3" * 64, "new_sha256": "3" * 64,
               "identical_inputs": True}
        a = dict(run, old_snapshot="snapshots/A/games.slim.csv", new_snapshot="snapshots/B/games.slim.csv")
        b = dict(run, checked_at="2026-10-07T16:58:20+00:00",
                 old_snapshot="snapshots/C/games.slim.csv", new_snapshot="snapshots/A/games.slim.csv")
        root = ET.fromstring(atom.build_detection_feed({"runs": [a, b]}, "https://example.invalid/"))
        ids = [e.findtext("a:id", namespaces=NS) for e in root.findall("a:entry", NS)]
        self.assertEqual(len(set(ids)), 2)

    def test_every_detection_entry_carries_the_candidate_not_correction_disclaimer(self):
        feed_json = json.loads(pathlib.Path(ROOT, "data", "alerts", "feed.json").read_text())
        root = ET.fromstring(atom.build_detection_feed(feed_json, "https://example.invalid/"))
        for e in root.findall("a:entry", NS):
            content = e.findtext("a:content", namespaces=NS)
            self.assertIn("not a confirmed official NFL/Elias correction", content)

    def test_an_empty_feed_publishes_an_explicit_no_comparison_entry(self):
        root = ET.fromstring(atom.build_detection_feed({"runs": []}, "https://example.invalid/"))
        titles = [e.findtext("a:title", namespaces=NS) for e in root.findall("a:entry", NS)]
        self.assertEqual(len(titles), 1)
        self.assertIn("No completed comparison recorded yet", titles[0])

    def test_alert_entries_carry_before_and_after_values(self):
        rep = report_with_alerts()
        entry = feed_mod.run_entry(rep, "old.csv", "new.csv")
        root = ET.fromstring(atom.build_detection_feed({"runs": [entry]}, "https://example.invalid/"))
        content = root.find("a:entry", NS).findtext("a:content", namespaces=NS)
        self.assertIn("24", content)
        self.assertIn("27", content)

    def test_corrections_feed_has_one_entry_per_record_and_links_the_archive(self):
        db = json.loads(pathlib.Path(ROOT, "data", "discrepancies.json").read_text())
        root = ET.fromstring(atom.build_corrections_feed(db, "https://example.invalid/"))
        entries = root.findall("a:entry", NS)
        self.assertEqual(len(entries), len(db["records"]))
        self.assertEqual(len({e.findtext("a:id", namespaces=NS) for e in entries}), len(entries))
        for e in entries:
            href = e.find("a:link", NS).get("href")
            self.assertTrue(href.startswith("https://web.archive.org/web/"), href)

    def test_corrections_entries_do_not_invent_a_publication_timestamp(self):
        """The archived pages print 'Sep 12' with no time, so the feed must use
        the build time and say so, rather than fabricating a timestamp."""
        db = json.loads(pathlib.Path(ROOT, "data", "discrepancies.json").read_text())
        xml_text = atom.build_corrections_feed(db, "https://example.invalid/")
        root = ET.fromstring(xml_text)
        built = db["meta"]["generated_at"].replace("Z", "") 
        for e in root.findall("a:entry", NS):
            self.assertTrue(e.findtext("a:updated", namespaces=NS).startswith(built[:10]))
        self.assertIn("no publication timestamp is invented", root.findtext("a:subtitle", namespaces=NS))

    def test_shipped_atom_files_parse_and_match_the_shipped_data(self):
        for path, count_from in (
            ("data/alerts/feed.atom", "data/alerts/feed.json"),
            ("data/corrections.atom", "data/discrepancies.json"),
        ):
            f = pathlib.Path(ROOT, path)
            self.assertTrue(f.exists(), f"{path} is not published")
            root = ET.parse(f).getroot()
            entries = root.findall("a:entry", NS)
            src = json.loads(pathlib.Path(ROOT, count_from).read_text())
            expected = len(src["runs"]) if "runs" in src else len(src["records"])
            self.assertEqual(len(entries), expected, f"{path} is out of step with {count_from}")


class TestFeedSourceHashes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_source_meta_reads_the_manifest_beside_the_snapshot(self):
        snap = os.path.join(self.tmp.name, "games.slim.csv")
        pathlib.Path(snap).write_text("x")
        pathlib.Path(snap + ".manifest.json").write_text(json.dumps(
            {"source_file_sha256": "f" * 64, "upstream_commit_sha": "c" * 40,
             "upstream_commit_date": "2026-10-07T19:45:00Z", "source_bytes": 2183215}))
        meta = feed_mod.source_meta(snap)
        self.assertEqual(meta["source_file_sha256"], "f" * 64)
        self.assertEqual(meta["upstream_commit_sha"], "c" * 40)

    def test_a_missing_manifest_yields_an_empty_dict_not_a_guessed_value(self):
        self.assertEqual(feed_mod.source_meta(os.path.join(self.tmp.name, "nope.csv")), {})

    def test_an_entry_records_both_the_compared_hash_and_the_source_hash(self):
        rep = report_with_alerts()
        entry = feed_mod.run_entry(rep, "/nonexistent/old.csv", "/nonexistent/new.csv")
        self.assertTrue(entry["identical_inputs"] is False or entry["identical_inputs"] is True)
        self.assertIn("source_file_changed", entry)
        self.assertIsNone(entry["source_file_changed"], "unknown must stay unknown")
        self.assertIn("identical_inputs_note", entry)

    def test_backfill_marks_annotated_entries_and_never_invents_a_hash(self):
        feed_json = {"runs": [{
            "checked_at": "2026-10-07T18:11:31+00:00",
            "old_snapshot": os.path.join(self.tmp.name, "old.csv"),
            "new_snapshot": os.path.join(self.tmp.name, "new.csv"),
            "identical_inputs": True,
        }]}
        for name, sha in (("old", "1" * 64), ("new", "2" * 64)):
            snap = os.path.join(self.tmp.name, f"{name}.csv")
            pathlib.Path(snap).write_text("x")
            pathlib.Path(snap + ".manifest.json").write_text(
                json.dumps({"source_file_sha256": sha}))
        touched = feed_mod.backfill_source_hashes(feed_json)
        self.assertEqual(touched, 1)
        run = feed_json["runs"][0]
        self.assertTrue(run["source_file_changed"])
        self.assertTrue(run["old_source"]["backfilled_from_manifest"])
        self.assertIn("did change", run["identical_inputs_note"])

    def test_shipped_feed_entries_record_whether_the_source_file_moved(self):
        """This is the correction to a claim the documentation got wrong: the
        recorded clean runs were described as no-ops, while the manifests beside
        them show the upstream file changed every time."""
        feed_json = json.loads(pathlib.Path(ROOT, "data", "alerts", "feed.json").read_text())
        self.assertTrue(feed_json["runs"], "the shipped feed records no runs")
        for r in feed_json["runs"]:
            self.assertIn("source_file_changed", r)
            self.assertIsNotNone(r["source_file_changed"],
                                 "a recorded run must state whether the source file moved")
            self.assertIn("identical_inputs_note", r)
        moved = [r for r in feed_json["runs"] if r["source_file_changed"]]
        self.assertTrue(moved, "no recorded run shows source movement; check the manifests")


class TestSchemaContract(unittest.TestCase):
    def raw(self):
        return json.loads(pathlib.Path(ROOT, "data", "verified_corrections_raw.json").read_text())

    def test_the_shipped_fact_layer_satisfies_the_contract(self):
        self.assertEqual(schema.validate(self.raw(), root=ROOT), [])

    def _expect(self, mutate, code):
        raw = self.raw()
        mutate(raw)
        codes = {p["code"] for p in schema.validate(raw, root=ROOT)}
        self.assertIn(code, codes, f"expected {code}, got {codes}")

    def test_an_unknown_source_id_is_rejected(self):
        self._expect(lambda r: r["corrections"][0].update(source_id="WAYBACK-NOPE"), "UNKNOWN_SOURCE")

    def test_a_row_outside_its_source_page_scope_is_rejected(self):
        self._expect(lambda r: r["corrections"][0].update(season=1999), "SCOPE_MISMATCH")

    def test_a_declared_row_count_that_does_not_match_is_rejected(self):
        self._expect(lambda r: r["sources"][0].update(rows_parsed=99), "COUNT_MISMATCH")

    def test_a_page_recorded_as_empty_but_with_rows_is_rejected(self):
        def m(r):
            empty = next(s for s in r["sources"] if s["expected_empty"])
            # Keep expected_empty TRUE and keep the declared count consistent, so
            # the only thing wrong is a row appearing on a page recorded as empty.
            r["corrections"].append({**r["corrections"][0], "source_id": empty["source_id"],
                                     "season": empty["season"], "week": empty["week"],
                                     "player": "Added Row"})
            empty["rows_parsed"] = 1
        self._expect(m, "EXPECTED_EMPTY_BUT_HAS_ROWS")

    def test_a_correction_with_no_change_is_rejected(self):
        self._expect(lambda r: r["corrections"][0].update(corrected_value=r["corrections"][0]["original_value"]),
                     "NO_CHANGE")

    def test_a_missing_value_is_rejected(self):
        self._expect(lambda r: r["corrections"][0].update(original_value=None), "MISSING_VALUE")

    def test_an_impossible_season_or_week_is_rejected(self):
        self._expect(lambda r: r["corrections"][0].update(week=41), "OUT_OF_RANGE")

    def test_a_url_that_is_not_an_archive_capture_is_rejected(self):
        self._expect(lambda r: r["sources"][0].update(url="https://fantasy.nfl.com/research/statcorrections"),
                     "NOT_AN_ARCHIVE_CAPTURE")

    def test_a_timestamp_that_disagrees_with_the_url_is_rejected(self):
        self._expect(lambda r: r["sources"][0].update(snapshot_timestamp="19990101000000"),
                     "TIMESTAMP_MISMATCH")

    def test_a_missing_evidence_artefact_is_rejected(self):
        self._expect(lambda r: r["sources"][0].update(evidence_artefact="data/evidence/pages/NOPE.md"),
                     "ARTEFACT_MISSING")

    def test_the_view_videos_parser_leak_is_rejected(self):
        self._expect(lambda r: r["corrections"][0].update(player="Case Keenum View Videos"), "PARSER_LEAK")

    def test_a_duplicated_row_is_rejected(self):
        self._expect(lambda r: r["corrections"].append(dict(r["corrections"][0])) and
                     r["sources"][0].update(rows_parsed=r["sources"][0]["rows_parsed"] + 1),
                     "DUPLICATE_ROW")

    def test_an_unparsed_row_cannot_ship_in_the_fact_layer(self):
        self._expect(lambda r: r["corrections"][0].update(parse_status="unparsed"), "UNPARSED_ROW")

    def test_an_unrecognised_position_filter_is_rejected(self):
        self._expect(lambda r: r["sources"][0].update(position_filter="QB"), "UNKNOWN_FILTER")

    def test_an_unexpected_key_is_surfaced_not_ignored(self):
        self._expect(lambda r: r["corrections"][0].update(settled_bet=True), "UNEXPECTED_KEY")

    def test_a_malformed_date_is_rejected(self):
        self._expect(lambda r: r["corrections"][0].update(correction_date="September 31st"), "BAD_DATE")


class TestStableRecordIds(unittest.TestCase):
    """P1-4: `record_id` used to be a positional ordinal. Adding rows silently
    re-pointed every external citation at a different correction."""

    def tmpdir(self):
        return tempfile.TemporaryDirectory()

    def write_inputs(self, root, corrections):
        raw_path = os.path.join(root, "raw.json")
        games_path = os.path.join(root, "games.csv")
        pathlib.Path(raw_path).write_text(json.dumps({
            "_README": ["test"], "generated_at": "2026-10-07T00:00:00Z", "generator": "test",
            "sources": [{
                "source_id": "WAYBACK-TEST", "publisher": "p", "page_title": "t",
                "snapshot_timestamp": "20191019100813",
                "url": "https://web.archive.org/web/20191019100813/https://fantasy.nfl.com/x",
                "live_url_now_retired": "https://fantasy.nfl.com/x", "season": 2013, "week": 1,
                "position_filter": "O", "evidence_artefact": "data/evidence/pages/2013-W01-O.md",
                "retrieval_channel": "test", "expected_empty": False,
                "rows_parsed": len(corrections)}],
            "corrections": corrections,
        }))
        pathlib.Path(games_path).write_text(
            "game_id,season,week,gameday,weekday,away_team,home_team,away_score,home_score,"
            "result,total,overtime,spread_line,total_line\n"
            "2013_01_DET_MIN,2013,1,2013-09-08,Sunday,DET,MIN,34,24,10,58,0,-3,47.5\n"
            "2013_01_PIT_TEN,2013,1,2013-09-08,Sunday,PIT,TEN,9,16,-7,25,0,-3,41.5\n")
        return raw_path, games_path

    def correction(self, player, stat, original, corrected, date="Sep 12"):
        return {"source_id": "WAYBACK-TEST", "season": 2013, "week": 1, "player": player,
                "position": "QB", "team": "DET", "correction_date": date, "stat": stat,
                "original_value": original, "corrected_value": corrected,
                "published_points_delta": 0.0, "raw_stat_text": f"{stat} changed from {original} to {corrected}.",
                "parse_status": "parsed"}

    def test_adding_a_row_never_changes_an_existing_id(self):
        with self.tmpdir() as tmp:
            first = [self.correction("Matthew Stafford", "Rushing Yards", 2.0, -3.0)]
            raw, games = self.write_inputs(tmp, first)
            _, rows_a = build_database.build(raw, games)

            second = [self.correction("Someone Else", "Receiving Yards", 0.0, 31.0)] + first
            raw, games = self.write_inputs(tmp, second)
            _, rows_b = build_database.build(raw, games)

            ida = {r["player"]: r["record_id"] for r in rows_a}
            idb = {r["player"]: r["record_id"] for r in rows_b}
            self.assertEqual(ida["Matthew Stafford"], idb["Matthew Stafford"])
            self.assertNotEqual(idb["Matthew Stafford"], idb["Someone Else"])

    def test_ids_are_unique_and_content_derived(self):
        with self.tmpdir() as tmp:
            rows_in = [self.correction("A", "Rushing Yards", 1.0, 2.0),
                       self.correction("B", "Receptions", 0.0, 3.0)]
            raw, games = self.write_inputs(tmp, rows_in)
            _, rows = build_database.build(raw, games)
            ids = [r["record_id"] for r in rows]
            self.assertEqual(len(set(ids)), 2)
            for r in rows:
                self.assertRegex(r["record_id"], r"^SC-[0-9A-F]{10}$")
                self.assertIn("record_ordinal", r)

    def test_identical_rows_still_get_distinct_ids(self):
        dup = self.correction("A", "Rushing Yards", 1.0, 2.0)
        ids = build_database.assign_record_ids([dup, dict(dup), dict(dup)])
        self.assertEqual(len(set(ids)), 3)

    def test_the_shipped_database_has_unique_stable_ids(self):
        db = json.loads(pathlib.Path(ROOT, "data", "discrepancies.json").read_text())
        ids = [r["record_id"] for r in db["records"]]
        self.assertEqual(len(set(ids)), len(ids))
        for r in db["records"]:
            self.assertRegex(r["record_id"], r"^SC-[0-9A-F]{10}$")
        ordinals = sorted(r["record_ordinal"] for r in db["records"])
        self.assertEqual(ordinals, list(range(1, len(db["records"]) + 1)))

    def test_a_record_id_can_be_recomputed_from_the_row_alone(self):
        """The id must be derivable from content, otherwise it is not stable."""
        raw = json.loads(pathlib.Path(ROOT, "data", "verified_corrections_raw.json").read_text())
        db = json.loads(pathlib.Path(ROOT, "data", "discrepancies.json").read_text())
        expected = build_database.assign_record_ids(raw["corrections"])
        by_ordinal = {r["record_ordinal"]: r["record_id"] for r in db["records"]}
        self.assertEqual({i + 1: e for i, e in enumerate(expected)}, by_ordinal)


class TestSourceMovementStudy(unittest.TestCase):
    PATH = os.path.join(ROOT, "data", "evidence", "upstream_churn_study.json")

    def study(self):
        if not os.path.exists(self.PATH):
            self.skipTest("no churn study published")
        return json.loads(pathlib.Path(self.PATH).read_text(encoding="utf-8"))

    def test_every_vintage_is_independently_re_downloadable(self):
        d = self.study()
        for v in d["vintages"]:
            if "error" in v:
                continue
            self.assertTrue(v["codeload_url"].startswith("https://codeload.github.com/nflverse/nfldata/tar.gz/"))
            self.assertEqual(len(v["sha256"]), 64)
            self.assertGreater(v["bytes"], 0)
            self.assertRegex(v["sha"], r"^[0-9a-f]{40}$")

    def test_the_totals_are_recomputable_from_the_pairs(self):
        d = self.study()
        pairs = d["pairs"]
        self.assertEqual(d["totals"]["frozen_field_changes_on_final_games"],
                         sum(p["detector_alerts"] for p in pairs))
        self.assertEqual(d["totals"]["non_frozen_field_changes_on_final_games"],
                         sum(p["non_frozen_change_count"] for p in pairs))
        self.assertEqual(d["totals"]["intervals_where_full_file_bytes_changed"],
                         sum(1 for p in pairs if p["full_file_changed"]))
        self.assertEqual(d["totals"]["final_records_compared"],
                         sum(p["final_records_in_old"] for p in pairs))
        self.assertEqual(d["sampling"]["intervals_compared"], len(pairs))

    def test_no_slim_change_is_left_unexplained(self):
        """If the frozen projection changed while no frozen value changed and no
        row was added or removed, our model of the projection is wrong."""
        d = self.study()
        self.assertEqual(d["totals"]["slim_changes_not_explained_by_frozen_or_row_count"], [])
        for p in d["pairs"]:
            if p["slim_changed"]:
                self.assertTrue(p["detector_alerts"] or p["final_records_delta"] != 0,
                                f"unexplained slim change in {p['new_commit']}")

    def test_every_observed_change_is_classified_as_backfill_or_revision(self):
        d = self.study()
        kinds = set()
        for p in d["pairs"]:
            for ch in p["non_frozen_changes_on_final_games"]:
                self.assertIn(ch["kind"], ("backfill_of_blank", "revision_of_published_value",
                                           "record_removed"))
                kinds.add(ch["kind"])
        self.assertEqual(sum(d["totals"]["change_kinds_on_final_games"].values()),
                         d["totals"]["non_frozen_field_changes_on_final_games"])
        self.assertTrue(kinds)

    def test_the_study_does_not_claim_to_measure_the_nfl(self):
        d = self.study()
        self.assertIn("Not a count of NFL/Elias corrections", d["meta"]["what_it_is_not"])
        self.assertIn("third-party mirror", d["source"]["provenance"])
        self.assertIn("bounded observation", d["interpretation"].lower())

    def test_the_sampling_blind_spot_is_quantified_not_hidden(self):
        d = self.study()
        self.assertGreaterEqual(d["sampling"]["stride"], 1)
        self.assertIn("blind spot", d["sampling"]["note"])
        self.assertIsNotNone(d["sampling"]["window_hours"])


class TestSiteSurfacesTheOperationalState(unittest.TestCase):
    def read(self, *parts):
        return pathlib.Path(ROOT, *parts).read_text(encoding="utf-8")

    def test_the_site_offers_both_subscribable_feeds(self):
        html = self.read("docs", "index.html")
        self.assertIn('type="application/atom+xml"', html)
        self.assertIn('href="data/alerts/feed.atom"', html)
        self.assertIn('href="data/corrections.atom"', html)
        self.assertIn('id="subscribe"', html)

    def test_the_site_renders_monitor_health_and_says_what_it_cannot_see(self):
        html = self.read("docs", "index.html")
        js = self.read("docs", "app.js")
        self.assertIn('id="health-headline"', html)
        self.assertIn('id="tbl-health"', html)
        self.assertIn("cannot see", html)
        self.assertIn("function renderHealth", js)
        self.assertIn("UNKNOWN", js)

    def test_the_site_renders_the_source_movement_study(self):
        html = self.read("docs", "index.html")
        js = self.read("docs", "app.js")
        self.assertIn('id="churn"', html)
        self.assertIn('id="tbl-churn-revisions"', html)
        self.assertIn("function renderChurn", js)
        self.assertIn("upstream_churn_study.json", js)

    def test_the_no_op_conflation_is_gone_from_the_site(self):
        """MUTATION GUARD for the wording error this session corrected."""
        js = self.read("docs", "app.js")
        self.assertNotIn("no-op rather than a fresh check", js)
        self.assertIn("source_file_changed", js)
        html = self.read("docs", "index.html")
        self.assertIn("Identical inputs\" is not the same as", html.replace("&quot;", '"'))

    def test_the_runs_table_has_a_column_for_source_movement(self):
        html = self.read("docs", "index.html")
        js = self.read("docs", "app.js")
        self.assertIn("Upstream source file", html)
        self.assertIn("colspan=\"6\"", js)

    def test_published_site_copies_are_in_sync(self):
        import filecmp
        for f in ("index.html", "app.js", "styles.css"):
            self.assertTrue(filecmp.cmp(os.path.join(ROOT, "docs", f),
                                        os.path.join(ROOT, f), shallow=False),
                            f"root {f} drifted from docs/{f}; run pipeline/sync_site_data.sh")
        for src, dst in (("data/alerts/feed.json", "docs/data/alerts/feed.json"),
                         ("data/alerts/feed.atom", "docs/data/alerts/feed.atom"),
                         ("data/alerts/health.json", "docs/data/alerts/health.json"),
                         ("data/corrections.atom", "docs/data/corrections.atom"),
                         ("data/evidence/upstream_churn_study.json",
                          "docs/data/upstream_churn_study.json")):
            self.assertTrue(filecmp.cmp(os.path.join(ROOT, src), os.path.join(ROOT, dst),
                                        shallow=False), f"{dst} drifted from {src}")


class TestWorkflows(unittest.TestCase):
    def read(self, name):
        return pathlib.Path(ROOT, ".github", "workflows", name).read_text(encoding="utf-8")

    def test_a_watchdog_exists_that_does_not_depend_on_the_detector(self):
        y = self.read("health.yml")
        self.assertIn("run.py health", y)
        self.assertIn("--fail-on fail", y)
        self.assertIn("schedule", y)

    def test_the_detector_does_not_gate_on_its_own_health(self):
        """Failing detect.yml on health would discard a good snapshot and make
        the next run repeat the same comparison."""
        y = self.read("detect.yml")
        self.assertIn("--fail-on none", y)

    def test_a_dead_lettered_notification_fails_the_run(self):
        y = self.read("detect.yml")
        self.assertIn("run.py deliver", y)
        self.assertIn('-eq 11', y)

    def test_notification_is_never_forced_on_a_fork(self):
        y = self.read("detect.yml")
        # The URL may only come from a repository secret, and its absence must be
        # tolerated rather than failing the run: a fork cannot be made to notify.
        self.assertIn("secrets.ALERT_WEBHOOK_URL", y)
        self.assertIn('[ -n "$WEBHOOK" ]', y)
        self.assertNotIn("https://hooks.slack.com/", y)
        self.assertNotIn("https://discord.com/api/webhooks/", y)

    def test_the_baseline_is_not_delivered_on_a_first_run(self):
        y = self.read("detect.yml")
        self.assertIn("steps.diff.outputs.baseline != 'true'", y)

    def test_the_merge_gate_validates_the_fact_layer_and_the_feeds(self):
        y = self.read("validate.yml")
        self.assertIn("pipeline/schema.py", y)
        self.assertIn("DUPLICATE ENTRY IDS", y)
        self.assertIn("upstream_churn_study.json", y)

    def test_the_churn_study_is_refreshed_on_a_schedule_of_its_own(self):
        y = self.read("source-churn.yml")
        self.assertIn("run.py churn", y)
        self.assertIn("cron", y)


if __name__ == "__main__":
    unittest.main(verbosity=2)
