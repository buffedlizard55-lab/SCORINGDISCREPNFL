"""
Tests for the scoring-discrepancy detection pipeline.

Run:  python3 -m pytest tests/ -q      (or)   python3 tests/test_pipeline.py

These tests encode the design rules that were derived empirically, so that a
future change cannot silently reintroduce the two bugs that were found and fixed
during review:
  (1) naive diffing flagging not-yet-played games,
  (2) classifying a 1-yard prop change as out-of-scope,
  (3) transparent gunzip breaking tar.gz consumers.
"""

from __future__ import annotations

import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "pipeline"))

import detect  # noqa: E402
from market_rules import classify, crosses_threshold, market_outcomes  # noqa: E402
from parse_corrections import parse_official_page, parse_markdown_rows  # noqa: E402


def make_row(**kw):
    base = {
        "game_id": "2026_01_AAA_BBB",
        "season": "2026",
        "week": "1",
        "away_team": "AAA",
        "home_team": "BBB",
        "away_score": "20",
        "home_score": "24",
        "result": "4",
        "total": "44",
        "overtime": "0",
        "spread_line": "-3",
        "total_line": "44.5",
    }
    base.update(kw)
    return base


class TestMarketRules(unittest.TestCase):
    def test_discrete_scoring_events_are_highest_severity(self):
        for stat in ["Touchdowns", "Passing Touchdowns", "Field Goals Made", "Extra Points Made", "Safeties", "Two Point Conversions"]:
            self.assertEqual(classify(stat, 0, 1)["severity"], 3, stat)

    def test_one_yard_prop_change_is_not_out_of_scope(self):
        # Regression: 182 -> 181 passing yards must NOT be dismissed.
        c = classify("Passing Yards", 182, 181)
        self.assertEqual(c["severity"], 2)
        self.assertEqual(c["category"], "line_priced_change")

    def test_round_number_crossing_detected(self):
        c = classify("Passing Yards", 299, 301)
        self.assertEqual(c["category"], "threshold_crossing")
        self.assertEqual(c["threshold"], 300.0)

    def test_crosses_threshold_semantics(self):
        self.assertTrue(crosses_threshold("Receiving Yards", 99, 101)[0])
        self.assertTrue(crosses_threshold("Receiving Yards", 101, 99)[0])
        self.assertFalse(crosses_threshold("Receiving Yards", 101, 102)[0])
        self.assertFalse(crosses_threshold("Bogus Stat", 1, 999)[0])

    def test_no_change_is_zero_severity(self):
        self.assertEqual(classify("Passing Yards", 100, 100)["severity"], 0)
        self.assertEqual(classify("Passing Yards", 100, 100)["category"], "no_change")

    def test_idp_tackle_is_low_but_market_relevant(self):
        c = classify("Tackle", 0, 1)
        self.assertEqual(c["severity"], 1)

    def test_market_outcomes_returns_list_for_every_branch(self):
        for args in [("Touchdowns", 0, 1), ("Passing Yards", 182, 181), ("Tackle", 0, 1), ("Zzz", 0, 1)]:
            self.assertIsInstance(market_outcomes(*args), list)

    def test_market_outcomes_never_crashes_on_none_threshold(self):
        # Regression: the sev-2 branch used to format c['threshold']:g, which
        # raised TypeError for line_priced_change rows where threshold is None.
        out = market_outcomes("Passing Yards", 182, 181)
        self.assertTrue(any("half-point line" in m for m in out))

    def test_scoring_event_lists_scoreboard_markets(self):
        out = market_outcomes("Touchdowns", 0, 1)
        self.assertIn("game total (over/under)", out)
        self.assertIn("point spread", out)


class TestDiffRules(unittest.TestCase):
    def test_rule1_not_yet_played_is_not_a_change(self):
        """A game with no result in the OLD snapshot must never be reported."""
        old = {"g1": make_row(result="", away_score="", home_score="", total="")}
        new = {"g1": make_row(away_score="21", home_score="28", result="7", total="49")}
        self.assertEqual(detect.diff_final_records(old, new, detect.FROZEN_FIELDS_GAMES), [])

    def test_rule2_line_movement_is_ignored(self):
        """Pre-game line churn on a final game must not be reported."""
        old = {"g1": make_row(spread_line="-3", total_line="44.5")}
        new = {"g1": make_row(spread_line="-5.5", total_line="46.5")}
        self.assertEqual(detect.diff_final_records(old, new, detect.FROZEN_FIELDS_GAMES), [])

    def test_real_score_revision_is_detected(self):
        old = {"g1": make_row(home_score="24", result="4", total="44")}
        new = {"g1": make_row(home_score="27", result="7", total="47")}
        changes = detect.diff_final_records(old, new, detect.FROZEN_FIELDS_GAMES)
        fields = {c.field_name for c in changes}
        self.assertEqual(fields, {"home_score", "result", "total"})
        for c in changes:
            self.assertEqual(c.old_value, {"home_score": "24", "result": "4", "total": "44"}[c.field_name])

    def test_vanished_record_is_flagged(self):
        old = {"g1": make_row()}
        self.assertEqual(len(detect.diff_final_records(old, {}, detect.FROZEN_FIELDS_GAMES)), 1)

    def test_load_csv_requires_a_key(self):
        with self.assertRaises(ValueError):
            detect.load_csv_rows(b"foo,bar\n1,2\n")


class TestAlerting(unittest.TestCase):
    def test_alert_carries_values_and_provenance(self):
        old = {"g1": make_row(home_score="24", result="4", total="44")}
        new = {"g1": make_row(home_score="27", result="7", total="47")}
        changes = detect.diff_final_records(old, new, detect.FROZEN_FIELDS_GAMES)
        report = detect.build_alert_report(changes, "test", min_severity=1)
        self.assertEqual(report["total_alerts"], 3)
        a = report["alerts"][0]
        self.assertIn("original_value", a)
        self.assertIn("corrected_value", a)
        self.assertIsNone(a["actually_changed_outcome"])  # never asserted by machine
        self.assertEqual(a["verification_status"], "detected_by_diff_pending_manual_confirmation")

    def test_all_frozen_game_fields_are_severity_3(self):
        """
        Any change to a frozen game field is a scoreboard change, so it must
        always surface at the top severity. This is what makes min_severity=3 a
        meaningful "scoreboard-only" watch mode.
        """
        old = {"g1": make_row(total="44")}
        new = {"g1": make_row(total="45")}
        changes = detect.diff_final_records(old, new, detect.FROZEN_FIELDS_GAMES)
        report = detect.build_alert_report(changes, "t", min_severity=3)
        self.assertEqual(report["total_alerts"], 1)
        self.assertEqual(report["alerts"][0]["severity"], 3)

    def test_min_severity_filters_lower_severity_changes(self):
        """A low-severity stat change must be droppable by min_severity."""
        low = detect.Change(
            key="p1",
            field_name="Tackle",
            old_value="0",
            new_value="1",
            context={"season": "2026", "week": "1"},
        )
        self.assertEqual(detect.build_alert_report([low], "t", min_severity=1)["total_alerts"], 1)
        self.assertEqual(detect.build_alert_report([low], "t", min_severity=3)["total_alerts"], 0)

    def test_markdown_renders_empty_and_populated(self):
        empty = detect.build_alert_report([], "t")
        self.assertIn("No qualifying discrepancies", detect.render_markdown(empty))
        old = {"g1": make_row(total="44")}
        new = {"g1": make_row(total="45")}
        md = detect.render_markdown(detect.build_alert_report(
            detect.diff_final_records(old, new, detect.FROZEN_FIELDS_GAMES), "t"))
        self.assertIn("| Severity | Game |", md)


class TestCorrectionsParser(unittest.TestCase):
    HTML = """
    <html><body>
    <table>
      <tr><th>Player</th><th>Date</th><th>Stat</th><th>Points</th></tr>
      <tr>
        <td><a href="/players/card?playerId=1">Cam Newton</a> <em>QB - CAR</em></td>
        <td>Dec 30</td><td>Tackle changed from <strong>0</strong> to <strong>1</strong>.</td><td>0.00</td>
      </tr>
      <tr>
        <td><a href="/x">Michael Clark</a> <em>WR - GB</em></td>
        <td>Dec 27</td><td>Receiving Yards changed from <strong>0</strong> to <strong>36</strong>.</td><td>3.60</td>
      </tr>
      <tr>
        <td><a href="/y">Ben Roethlisberger</a> <em>QB - PIT</em></td>
        <td>Dec 30</td><td>Passing Yards changed from <strong>215</strong> to <strong>220</strong>.</td><td>0.20</td>
      </tr>
    </table>
    </body></html>
    """

    def test_parses_players_stats_and_values(self):
        rows = parse_official_page(self.HTML, season=2015, week=16)
        self.assertEqual(len(rows), 3)
        clark = [r for r in rows if r.player == "Michael Clark"][0]
        self.assertEqual(clark.position, "WR")
        self.assertEqual(clark.team, "GB")
        self.assertEqual(clark.stat, "Receiving Yards")
        self.assertEqual(clark.original_value, 0.0)
        self.assertEqual(clark.corrected_value, 36.0)
        self.assertEqual(clark.numeric_change, 36.0)
        self.assertEqual(clark.parse_status, "parsed")
        self.assertEqual(clark.correction_date, "Dec 27")

    def test_negative_values_handled(self):
        html = ('<table><tr><td>Ben Roethlisberger <em>QB - PIT</em></td><td>Dec 30</td>'
                '<td>Receiving Yards changed from <b>-8</b> to <b>-3</b>.</td><td>0.50</td></tr></table>')
        r = parse_official_page(html)[0]
        self.assertEqual(r.original_value, -8.0)
        self.assertEqual(r.corrected_value, -3.0)
        self.assertEqual(r.numeric_change, 5.0)

    def test_unparsed_rows_are_preserved_not_dropped(self):
        html = ('<table><tr><td>Someone <em>RB - DAL</em></td><td>Dec 1</td>'
                '<td>Something unusual happened here</td><td>0.00</td></tr></table>')
        r = parse_official_page(html)[0]
        self.assertEqual(r.parse_status, "unparsed")
        self.assertEqual(r.raw_stat_text, "Something unusual happened here")
        self.assertIsNone(r.original_value)

    def test_empty_page_returns_empty_list(self):
        self.assertEqual(parse_official_page("<html>No stat corrections to display</html>"), [])

    def test_markdown_fallback(self):
        md = ("| Player | Date | Stat | Points |\n|---|---|---|---|\n"
              "| [Dak Prescott](http://x) _QB - DAL_ | Dec 26 | Passing Yards changed from 182 to 181. | -0.04 |\n")
        rows = parse_official_page(md)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].stat, "Passing Yards")
        self.assertEqual(rows[0].original_value, 182.0)
        self.assertEqual(rows[0].corrected_value, 181.0)

    def test_header_row_not_treated_as_data(self):
        rows = parse_official_page(self.HTML)
        self.assertNotIn("Player", [r.player for r in rows])


class TestShippedDatabase(unittest.TestCase):
    """Guards the shipped artefacts, including the 'no hallucination' contract."""

    DATA = os.path.join(os.path.dirname(HERE), "data")

    def _load(self, name):
        import json
        with open(os.path.join(self.DATA, name), encoding="utf-8") as f:
            return json.load(f)

    def test_every_record_has_a_reviewable_source_url(self):
        db = self._load("discrepancies.json")
        self.assertGreater(len(db["records"]), 0)
        for r in db["records"]:
            self.assertTrue(r["source_url_archived"].startswith("https://web.archive.org/"), r["record_id"])
            self.assertTrue(r["source_url_live_now_retired"].startswith("https://fantasy.nfl.com/"), r["record_id"])
            self.assertIn("NFL League Office", r["source_publisher"])
            self.assertIn("Elias", r["source_publisher"])

    def test_original_and_corrected_values_are_present_and_reproducible(self):
        db = self._load("discrepancies.json")
        for r in db["records"]:
            self.assertIsNotNone(r["original_value"], r["record_id"])
            self.assertIsNotNone(r["corrected_value"], r["record_id"])
            self.assertNotEqual(r["original_value"], r["corrected_value"], r["record_id"])
            self.assertAlmostEqual(
                r["numeric_change"], r["corrected_value"] - r["original_value"], places=6, msg=r["record_id"]
            )

    def test_no_record_claims_a_confirmed_outcome_change_without_proof(self):
        db = self._load("discrepancies.json")
        for r in db["records"]:
            if r["actually_changed_official_outcome"]:
                self.fail(f"{r['record_id']} asserts a realised outcome change; must be evidenced")

    def test_records_join_to_a_real_game(self):
        db = self._load("discrepancies.json")
        for r in db["records"]:
            self.assertFalse(
                [f for f in r["review_flags"] if "GAME_JOIN_FAILED" in f],
                f"{r['record_id']} failed to join to a game",
            )

    def test_team_codes_are_shown_as_the_era_they_played_in(self):
        """
        Regression: the join normalises franchise codes (STL -> LA, JAC -> JAX,
        SD -> LAC, OAK -> LV) and that normalised code was leaking into DISPLAY,
        so a 2015 Rams row rendered as "LA". Normalisation must be confined to
        matching; display must use the code as it was at the time, which is also
        exactly what the official source page printed.
        """
        db = self._load("discrepancies.json")
        by_player = {}
        for r in db["records"]:
            by_player.setdefault(r["player"], []).append(r)

        gurley = by_player.get("Todd Gurley")
        self.assertIsNotNone(gurley, "expected the 2015 Todd Gurley row")
        self.assertEqual(gurley[0]["team"], "STL", "2015 Rams must display as STL, not LA")

        # Any row whose normalised code differs must show the original, and the
        # two must be recorded separately so the join stays reproducible.
        for r in db["records"]:
            self.assertIn("team_normalized", r, r["record_id"])
            self.assertNotIn(
                r["team"], ("", None), f"{r['record_id']} lost its as-printed team code"
            )

        # And the 2015 Rams game itself must show STL on both sides of the join.
        for r in db["records"]:
            if r.get("game_id") == "2015_16_STL_SEA":
                self.assertIn("STL", (r["away_team"], r["home_team"]))
                break

    def test_score_integrity_study_is_present_and_reports_its_caveat(self):
        st = self._load(os.path.join("evidence", "score_integrity_study.json"))
        self.assertGreater(st["totals"]["game_snapshots_examined"], 1000)
        self.assertIn("caveat", st)
        self.assertIn("MIRROR", st["caveat"])

    def test_market_sensitivity_is_framed_as_sensitivity_not_occurrence(self):
        ms = self._load("market_sensitivity_2025_2026.json")
        self.assertIn("Sensitivity only", ms["summary"]["framing"])
        self.assertGreater(ms["summary"]["games_considered_with_scores_and_lines"], 0)


class TestSiteDataContract(unittest.TestCase):
    """
    The site reads shipped JSON by field name. A rename in the builder silently
    blanks out a column on the page instead of failing loudly.

    This guard was added after exactly that bug shipped into a draft: the
    builder emits `game_date` while the site still read `gameday`, which would
    have rendered every game date as an em-dash. The test now fails the build
    instead.
    """

    ROOT = os.path.dirname(HERE)

    def test_fields_the_site_reads_all_exist_in_the_shipped_data(self):
        import json
        import re

        def read(p):
            with open(os.path.join(self.ROOT, p), encoding="utf-8") as f:
                return f.read()

        html = read("docs/index.html")
        js_full = read("docs/app.js")
        with open(os.path.join(self.ROOT, "docs", "data", "discrepancies.json"), encoding="utf-8") as f:
            db = json.load(f)
        with open(os.path.join(self.ROOT, "docs", "data", "market_sensitivity_2025_2026.json"), encoding="utf-8") as f:
            ms = json.load(f)

        # `r` is also the name of the fetch Response inside loadJSON(), so scan
        # only the rendering code after that helper. Without this, the guard
        # produces a false positive on `r.status`.
        marker = "function renderTopCards"
        self.assertIn(marker, js_full, "app.js structure changed; update this guard")
        js = js_full[js_full.index(marker):]

        record_fields = set()
        for r in db["records"]:
            record_fields |= set(r)

        # every data-k="..." sortable column must exist on the records
        for k in set(re.findall(r'data-k="([^"]+)"', html)):
            self.assertIn(k, record_fields, f"sortable column '{k}' is not a field on any record")

        # every r.<field> / r['field'] access in app.js must exist too
        for k in set(re.findall(r"\br\.([a-z_][a-z0-9_]*)", js)):
            self.assertIn(
                k, record_fields,
                f"app.js reads r.{k} but no record has that field — the column would render blank",
            )

        # the market-sensitivity game rows have their own contract
        game_fields = set(ms["games"][0])
        for k in set(re.findall(r"\bg\.([a-z_][a-z0-9_]*)", js)):
            self.assertIn(k, game_fields, f"app.js reads g.{k} which is not on market-sensitivity rows")

    def test_root_site_copies_match_the_canonical_docs_copies(self):
        """
        GitHub Pages for this repo publishes from the repository ROOT (a setting
        the available token cannot change), while docs/ stays canonical. The
        root files are generated from docs/ by pipeline/sync_site_data.sh, so
        they must stay byte-identical or the live site silently goes stale.
        """
        import filecmp

        for f in ["index.html", "app.js", "styles.css", ".nojekyll"]:
            docs_f = os.path.join(self.ROOT, "docs", f)
            root_f = os.path.join(self.ROOT, f)
            self.assertTrue(os.path.exists(docs_f), f"missing canonical docs/{f}")
            self.assertTrue(
                os.path.exists(root_f),
                f"missing root {f} — GitHub Pages publishes from the root, so the "
                f"site would be blank. Run pipeline/sync_site_data.sh",
            )
            self.assertTrue(
                filecmp.cmp(docs_f, root_f, shallow=False),
                f"root {f} has drifted from docs/{f} — run pipeline/sync_site_data.sh",
            )

    def test_app_js_can_resolve_data_in_both_published_layouts(self):
        """
        One app.js is published twice (root and docs/) where the study artefact
        sits at different relative paths. It must therefore try both.
        """
        with open(os.path.join(self.ROOT, "docs", "app.js"), encoding="utf-8") as f:
            js = f.read()
        self.assertIn("loadFirst", js, "app.js lost its multi-layout data resolution")
        self.assertIn("data/score_integrity_study.json", js)
        self.assertIn("data/evidence/score_integrity_study.json", js)

    def test_site_data_files_are_in_sync_with_the_source_of_truth(self):
        """docs/data must be a byte-identical copy of data/ so the page cannot drift."""
        import filecmp

        pairs = [
            ("data/discrepancies.json", "docs/data/discrepancies.json"),
            ("data/evidence/score_integrity_study.json", "docs/data/score_integrity_study.json"),
            ("data/market_sensitivity_2025_2026.json", "docs/data/market_sensitivity_2025_2026.json"),
        ]
        for src, dst in pairs:
            s, d = os.path.join(self.ROOT, src), os.path.join(self.ROOT, dst)
            self.assertTrue(os.path.exists(s), f"missing {src}")
            self.assertTrue(os.path.exists(d), f"missing {dst}")
            self.assertTrue(
                filecmp.cmp(s, d, shallow=False),
                f"{dst} has drifted from {src} — re-copy it or the site will show stale data",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
