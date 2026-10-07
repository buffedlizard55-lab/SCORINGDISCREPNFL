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

import csv
import io
import json
import pathlib
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "pipeline"))

import detect  # noqa: E402
import run as pipeline_run  # noqa: E402
import fetch as pipeline_fetch  # noqa: E402
from build_database import parse_correction_date  # noqa: E402
from market_rules import classify, crosses_threshold, market_outcomes  # noqa: E402
from market_sensitivity import analyse as analyse_market_sensitivity  # noqa: E402
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
    def test_player_scoring_stats_are_high_priority_but_not_scoreboard_proof(self):
        for stat in ["Touchdowns", "Passing Touchdowns", "Field Goals Made", "Extra Points Made", "Safeties", "Two Point Conversions"]:
            result = classify(stat, 0, 1)
            self.assertEqual(result["severity"], 3, stat)
            self.assertIn("does not", result["reason"], stat)

        markets = market_outcomes("Passing Touchdowns", 0, 1)
        self.assertTrue(any("passing-touchdown" in item for item in markets))
        self.assertTrue(any("unproven" in item for item in markets))
        self.assertFalse(any("game total (over/under)" == item for item in markets))

    def test_attempt_stats_do_not_imply_a_scoring_event(self):
        for stat in ["Field Goals Attempted", "Extra Points Attempted"]:
            self.assertEqual(classify(stat, 0, 1)["severity"], 2, stat)
            self.assertEqual(classify(stat, 0, 1)["category"], "line_priced_change", stat)

    def test_one_yard_prop_change_is_not_out_of_scope(self):
        # Regression: 182 -> 181 passing yards must NOT be dismissed.
        c = classify("Passing Yards", 182, 181)
        self.assertEqual(c["severity"], 2)
        self.assertEqual(c["category"], "line_priced_change")
        self.assertIn("hypothetical", c["reason"])
        self.assertIn("if such a market was actually offered", c["reason"])

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

    def test_player_touchdown_stat_does_not_claim_game_score_markets(self):
        out = market_outcomes("Touchdowns", 0, 1)
        self.assertTrue(any("touchdown" in item for item in out))
        self.assertFalse(any(item == "game total (over/under)" for item in out))
        self.assertFalse(any(item == "point spread" for item in out))

    def test_game_score_alert_maps_to_direct_market_fields(self):
        change = detect.Change(
            key="g1",
            field_name="home_score",
            old_value="24",
            new_value="27",
            context={"home_team": "BBB", "away_team": "AAA"},
        )
        alert = detect.change_to_alert(change, "test", "2026-10-07T00:00:00Z")
        self.assertIn("BBB team total, if offered", alert["markets_potentially_affected"])
        self.assertIn("game total (over/under), if offered", alert["markets_potentially_affected"])
        self.assertIn("point spread, if offered", alert["markets_potentially_affected"])


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

    def test_webhook_uses_discord_payload_shape(self):
        report = detect.build_alert_report(
            [detect.Change("g1", "home_score", "24", "27")], "test", min_severity=1
        )

        class Response:
            status = 204
            def __enter__(self): return self
            def __exit__(self, *args): return False

        with patch("urllib.request.urlopen", return_value=Response()) as opener:
            ok, message = detect.notify_webhook(report, "https://discord.com/api/webhooks/1/token")
        self.assertTrue(ok)
        self.assertEqual(message, "http 204")
        payload = json.loads(opener.call_args.args[0].data.decode("utf-8"))
        self.assertIn("content", payload)
        self.assertNotIn("text", payload)

    def test_webhook_uses_slack_payload_shape_and_review_link(self):
        report = detect.build_alert_report(
            [detect.Change("g1", "home_score", "24", "27", {"season": "2026", "week": "1", "away_team": "AAA", "home_team": "BBB"})],
            "test",
            min_severity=1,
        )
        report["review_url"] = "https://github.com/example/repo/actions/runs/123"

        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False

        with patch("urllib.request.urlopen", return_value=Response()) as opener:
            ok, _ = detect.notify_webhook(report, "https://hooks.slack.com/services/test")
        self.assertTrue(ok)
        payload = json.loads(opener.call_args.args[0].data.decode("utf-8"))
        self.assertIn("text", payload)
        self.assertNotIn("content", payload)
        self.assertIn("Unconfirmed NFL results-mirror change candidate", payload["text"])
        self.assertIn("not confirmation", payload["text"])
        self.assertIn("24 → 27", payload["text"])
        self.assertIn("https://github.com/example/repo/actions/runs/123", payload["text"])

    def test_empty_webhook_report_does_not_send(self):
        with patch("urllib.request.urlopen") as opener:
            ok, message = detect.notify_webhook(detect.build_alert_report([], "test"), "https://hooks.slack.com/services/test")
        self.assertTrue(ok)
        self.assertIn("no alerts", message)
        opener.assert_not_called()

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

    def test_correction_cli_scope_and_archived_review_url(self):
        url = "https://fantasy.nfl.com/research/statcorrections?position=O&statSeason=2015&statWeek=16"
        self.assertEqual(pipeline_run.correction_scope_from_url(url), (2015, 16))
        self.assertEqual(pipeline_run.correction_scope_from_url("https://example.test/", 2018), (2018, None))
        self.assertEqual(
            pipeline_fetch.official_corrections_snapshot_url("20200930215056", url),
            "https://web.archive.org/web/20200930215056/" + url,
        )

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


class TestRealArchivedPageContent(unittest.TestCase):
    """
    Regression tests built from REAL archived official page content, not from
    hand-written idealised fixtures.

    WHY THIS CLASS EXISTS
    ---------------------
    On 2026-10-07 the parser was run against real archived page text for the
    first time. It produced ZERO usable rows, for two reasons that the existing
    fixture could not catch:

      1. The real page bolds the numbers ("Tackle changed from **0** to **1**.").
         _RE_CHANGED's numeric class cannot match "**0**", so every row fell
         through to parse_status="unparsed". The old fixture had omitted the
         asterisks, which is why the suite was green while the parser was broken.
      2. A player with a highlight reel renders a second link in the same cell,
         producing player names like "Case Keenum    View Videos".

    These tests fail loudly if either bug ever returns.
    """

    PAGES_DIR = os.path.join(DATA_DIR, "evidence", "pages")

    # Verbatim lines from the archived 2018 W14 and 2010 W1 pages.
    REAL_BOLD_NUMBERS = (
        "| [Darrius Heyward-Bey](https://web.archive.org/web/20181219090041/x"
        "?leagueId=0&playerId=80427) _WR - PIT_ | Dec 12 "
        "| Tackle changed from **0** to **1**. | 0.00 |\n"
    )
    REAL_VIEW_VIDEOS = (
        "| [Case Keenum](https://web.archive.org/web/20181219090041/y"
        "?leagueId=0&playerId=2532888) _QB - DEN_ "
        '[View Videos](https://web.archive.org/web/20181219090041/z "View Player Videos") '
        "| Dec 12 | Rushing Yards changed from **71** to **67**. | -0.40 |\n"
    )
    REAL_DEF_NICKNAME = (
        "| [Green Bay Packers](https://web.archive.org/web/20260516203131/w"
        "?leagueId=0&playerId=100011) _DEF_ | Sep 15 "
        "| Sacks changed from **5** to **6**. | 1.00 |\n"
    )
    REAL_NEGATIVE_VALUES = (
        "| [Ben Roethlisberger](https://web.archive.org/web/20200930215056/v) _QB - PIT_ "
        "| Dec 30 | Receiving Yards changed from **-8** to **-3**. | 0.50 |\n"
    )

    def test_bold_numbers_are_parsed_not_dropped(self):
        """Bug 1: '**0**' must yield 0.0, not parse_status='unparsed'."""
        rows = parse_official_page(self.REAL_BOLD_NUMBERS, season=2018, week=14)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r.parse_status, "parsed", r.raw_stat_text)
        self.assertEqual(r.stat, "Tackle")
        self.assertEqual(r.original_value, 0.0)
        self.assertEqual(r.corrected_value, 1.0)
        self.assertEqual(r.numeric_change, 1.0)
        self.assertEqual(r.position, "WR")
        self.assertEqual(r.team, "PIT")

    def test_view_videos_link_never_leaks_into_the_player_name(self):
        """Bug 2: the trailing highlight-reel link is not part of the name."""
        rows = parse_official_page(self.REAL_VIEW_VIDEOS, season=2018, week=14)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].player, "Case Keenum")
        self.assertNotIn("View", rows[0].player)
        self.assertEqual(rows[0].corrected_value, 67.0)

    def test_defensive_unit_rows_resolve_position_without_a_team_code(self):
        """DEF rows print a nickname and no code; name must survive intact."""
        rows = parse_official_page(self.REAL_DEF_NICKNAME, season=2010, week=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].player, "Green Bay Packers")
        self.assertEqual(rows[0].position, "DEF")
        self.assertIsNone(rows[0].team)
        self.assertEqual(rows[0].stat, "Sacks")
        self.assertEqual(rows[0].corrected_value, 6.0)

    def test_negative_values_survive_normalisation(self):
        rows = parse_official_page(self.REAL_NEGATIVE_VALUES, season=2015, week=16)
        self.assertEqual(rows[0].original_value, -8.0)
        self.assertEqual(rows[0].corrected_value, -3.0)
        self.assertEqual(rows[0].numeric_change, 5.0)

    # --- shapes discovered while expanding the database on 2026-10-07 -------
    # These are verbatim lines from newly stored artefacts, not invented
    # fixtures. Each one is a cell shape the parser had never seen.

    REAL_HALF_SACK = (
        "| [Earl Thomas](https://web.archive.org/web/20251212134358/https://fantasy.nfl.com"
        "/players/card?leagueId=0&playerId=2508080) _DB - BAL_ | Dec 24 "
        "| Sack changed from **0** to **0.5**. | 0.00 |\n"
    )
    REAL_INJURY_TAG_Q = (
        "| [D.J. Chark](https://web.archive.org/web/20251108074922/https://fantasy.nfl.com"
        "/players/card?leagueId=0&playerId=2561018) _WR - JAX_ **Q** | Dec 30 "
        "| Tackle changed from **1** to **0**. | 0.00 |\n"
    )
    REAL_INJURY_TAG_IA = (
        "| [Kenneth Murray Jr.](https://web.archive.org/web/20260123193129/https://fantasy.nfl.com"
        "/players/card?leagueId=0&playerId=2565063) _LB - TEN_ **IA** | Dec 27 "
        "| Tackle changed from **2** to **3**. | 0.00 |\n"
    )

    def test_half_sack_is_parsed_as_a_float(self):
        """A shared sack is 0.5. Rounding it to an integer would corrupt the change."""
        rows = parse_official_page(self.REAL_HALF_SACK, season=2019, week=16)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r.parse_status, "parsed", r.raw_stat_text)
        self.assertEqual(r.player, "Earl Thomas")
        self.assertEqual(r.position, "DB")
        self.assertEqual(r.team, "BAL")
        self.assertEqual(r.stat, "Sack")
        self.assertEqual(r.original_value, 0.0)
        self.assertEqual(r.corrected_value, 0.5)
        self.assertAlmostEqual(r.numeric_change, 0.5, places=6)

    def test_injury_tag_is_not_swallowed_into_the_player_name(self):
        """The page bolds an injury designation after the team: '_WR - JAX_ **Q**'."""
        rows = parse_official_page(self.REAL_INJURY_TAG_Q, season=2020, week=16)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].player, "D.J. Chark")
        self.assertEqual(rows[0].team, "JAX")
        self.assertEqual(rows[0].position, "WR")

    def test_injury_tag_does_not_break_a_dotted_suffix_name(self):
        """'Kenneth Murray Jr.' + '**IA**': the suffix must survive, the tag must not."""
        rows = parse_official_page(self.REAL_INJURY_TAG_IA, season=2023, week=16)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].player, "Kenneth Murray Jr.")
        self.assertEqual(rows[0].team, "TEN")
        self.assertNotIn("IA", rows[0].player)

    def test_every_artefact_declares_the_metadata_the_database_needs(self):
        """A page with no season/week/url cannot be joined or reviewed — fail loudly."""
        import re as _re

        pages = sorted(pathlib.Path(self.PAGES_DIR).glob("*.md"))
        self.assertGreaterEqual(len(pages), 10)
        for p in pages:
            text = p.read_text(encoding="utf-8")
            head = "\n".join(l for l in text.splitlines() if l.startswith("#"))
            # Check line by line: `^` is not MULTILINE under assertRegex, so a
            # single joined-string match would only ever test the first line.
            keys = {}
            for line in text.splitlines():
                if line.startswith("#"):
                    m = _re.match(r"^#\s?([a-z_]+):\s?(.*)$", line)
                    if m and m.group(1) not in keys:
                        keys[m.group(1)] = m.group(2).strip()
            for key in ("url", "snapshot_timestamp", "season", "week"):
                self.assertIn(key, keys, f"{p.name} is missing `{key}`")
            self.assertTrue(keys["snapshot_timestamp"].isdigit(),
                            f"{p.name} snapshot_timestamp is not a Wayback stamp")
            self.assertIn("retrieval_channel", head, f"{p.name} does not say how it was retrieved")
            # `expect_empty` is the only thing that legitimises a zero-row artefact.
            if "No stat corrections to display" in text:
                self.assertIn("expect_empty: true", head,
                              f"{p.name} is empty but is not marked expect_empty")
            m = _re.search(r"^#\s?url:\s?(https://web\.archive\.org/web/\d+/)", head, _re.M)
            self.assertIsNotNone(m, f"{p.name} url is not an archived Wayback capture")

    def test_every_row_is_reproducible_from_its_stored_evidence_artefact(self):
        """
        Line-by-line audit. The brief requires verification, not assertion.

        For every shipped row this re-derives the stat name, the original value
        and the corrected value from the row's own raw source text, then checks
        that the raw text, the player and the correction date appear LITERALLY in
        the stored archived-page artefact it claims to come from.

        A transcription error therefore fails the build instead of shipping a
        plausible-looking number under a real player's name.
        """
        import json as _json
        import re as _re

        from parse_corrections import normalize_cell

        raw = _json.loads(pathlib.Path(DATA_DIR, "verified_corrections_raw.json").read_text(encoding="utf-8"))

        artefacts = {}
        for p in sorted((pathlib.Path(DATA_DIR) / "evidence" / "pages").glob("*.md")):
            text = p.read_text(encoding="utf-8")
            head = {}
            for line in text.splitlines():
                if line.startswith("#"):
                    m = _re.match(r"^#\s?([a-z_]+):\s?(.*)$", line)
                    if m:
                        head.setdefault(m.group(1), m.group(2).strip())
            # Normalise exactly the way the parser does, so the comparison is
            # between like and like (bold markers become spaces).
            norm = "\n".join(normalize_cell(l) for l in text.splitlines())
            artefacts[p.name] = (head, norm)

        changed = _re.compile(
            r"^(?P<stat>.+?)\s+changed\s+from\s+(?P<old>-?[\d.]+)\s+to\s+(?P<new>-?[\d.]+)", _re.I
        )
        src_by_id = {s["source_id"]: s for s in raw["sources"]}

        self.assertGreater(len(raw["corrections"]), 0)
        for c in raw["corrections"]:
            where = f"{c['source_id']} / {c['player']} / {c['stat']}"
            st = c["raw_stat_text"]
            m = changed.match(st)
            self.assertIsNotNone(m, f"unparseable raw text for {where}")
            self.assertEqual(m.group("stat").strip(), c["stat"], where)
            self.assertEqual(float(m.group("old")), c["original_value"], where)
            self.assertEqual(float(m.group("new")), c["corrected_value"], where)

            matches = [n for n, (h, _) in artefacts.items() if h.get("source_id") == c["source_id"]]
            self.assertEqual(len(matches), 1, f"{c['source_id']} does not match exactly one artefact")
            head, norm = artefacts[matches[0]]

            self.assertIn(st, norm, f"stat text not present in {matches[0]} for {where}")
            self.assertIn(str(c["player"]), norm, f"player not present in {matches[0]} for {where}")
            self.assertIn(str(c["correction_date"]), norm, f"date not present in {matches[0]} for {where}")
            self.assertEqual(int(head["season"]), c["season"], where)
            self.assertEqual(int(head["week"]), c["week"], where)
            self.assertEqual(head.get("url"), src_by_id[c["source_id"]]["url"], where)

    def test_database_covers_defensive_stat_categories_named_in_the_brief(self):
        """
        The brief names sacks and defensive credits explicitly. 'All Offense'
        filters never return them, so the database must contain IDP rows.
        """
        import json as _json

        with open(os.path.join(DATA_DIR, "discrepancies.json"), encoding="utf-8") as fh:
            records = _json.load(fh)["records"]
        stats = {r["stat"] for r in records}
        self.assertIn("Sack", stats, "no individual sack correction in the database")
        positions = {r["position"] for r in records}
        self.assertTrue(positions & {"DB", "LB", "DL"},
                        "no individual defensive player (IDP) corrections")
        self.assertIn("DEF", positions, "no team-defence corrections")

    def test_every_stored_artefact_parses_cleanly(self):
        """
        The shipped artefacts ARE the evidence for the database. If any of them
        stops parsing, the database is no longer reproducible.
        """
        import ingest_rendered  # noqa: E402

        pages = sorted(pathlib.Path(self.PAGES_DIR).glob("*.md"))
        self.assertGreaterEqual(len(pages), 4, "expected the shipped evidence artefacts")

        doc = ingest_rendered.ingest()
        self.assertEqual(doc["_problems"], [], "irregularities flagged during ingest")
        self.assertGreater(len(doc["corrections"]), 0)
        for c in doc["corrections"]:
            self.assertEqual(c["parse_status"], "parsed", c)
            self.assertIsNotNone(c["player"], c)
            self.assertIsNotNone(c["stat"], c)
            self.assertIsNotNone(c["original_value"], c)
            self.assertIsNotNone(c["corrected_value"], c)

    def test_raw_database_is_reproducible_from_the_artefacts(self):
        """No hand-editing the derived raw layer: it must regenerate byte-for-byte."""
        import ingest_rendered  # noqa: E402

        doc = ingest_rendered.ingest()
        doc.pop("_problems", None)
        import json as _json
        blob = _json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
        stored = pathlib.Path(ingest_rendered.RAW_PATH).read_text(encoding="utf-8")
        # `generated_at` legitimately differs between runs; compare the payload.
        strip = lambda s: _json.loads(s)
        a, b = strip(blob), strip(stored)
        a.pop("generated_at", None)
        b.pop("generated_at", None)
        self.assertEqual(a, b, "run: python3 pipeline/ingest_rendered.py --write")

    def test_team_nickname_table_only_contains_real_schedule_codes(self):
        """
        The nickname->code table is the one place a typo or an invented code
        could enter the database. Every code it maps to must actually occur in
        the versioned third-party schedule snapshot we ship.
        """
        from build_database import TEAM_NAME_TO_CODE, TEAM_ALIASES

        snap = sorted(pathlib.Path(DATA_DIR).parent.glob("snapshots/nfldata_games/*/games.slim.csv"))
        self.assertTrue(snap, "no schedule snapshot to validate against")
        import csv as _csv
        real = set()
        with open(snap[-1], newline="", encoding="utf-8-sig") as f:
            for row in _csv.DictReader(f):
                real.add(row["away_team"])
                real.add(row["home_team"])
        self.assertGreater(len(real), 30)

        for nickname, code in TEAM_NAME_TO_CODE.items():
            target = TEAM_ALIASES.get(code, code)
            self.assertIn(
                target, real,
                f"TEAM_NAME_TO_CODE['{nickname}'] = {code!r} (-> {target}) is not a "
                f"team code that occurs in the versioned third-party schedule",
            )
        self.assertEqual(len(TEAM_NAME_TO_CODE), 37)


class TestDocumentationIntegrity(unittest.TestCase):
    """The docs make link promises. Two were broken on 2026-10-07; this keeps them fixed."""

    def test_no_broken_relative_links_in_markdown(self):
        import re as _re
        broken = []
        for md in pathlib.Path(ROOT).rglob("*.md"):
            if ".git" in md.parts or "node_modules" in md.parts:
                continue
            text = md.read_text(encoding="utf-8", errors="replace")
            for m in _re.finditer(r"\[([^\]]+)\]\(([^)#]+)(#[^)]*)?\)", text):
                link = m.group(2).strip()
                if not link or link.startswith(("http://", "https://", "mailto:")):
                    continue
                if not (md.parent / link).resolve().exists():
                    broken.append(f"{md.relative_to(ROOT)}: {link}")
        self.assertEqual(broken, [], "broken relative links: " + "; ".join(broken))

    def test_readme_contains_the_governing_brief_verbatim(self):
        """The brief is the acceptance criteria; it must stay in the README in full."""
        readme = pathlib.Path(ROOT, "README.md").read_text(encoding="utf-8")
        for phrase in (
            "NFL Scoring Discrepancy Investigation",
            "Elias Sports Bureau",
            "No hallucinations",
            "It should solve the problem of having to manually check everything ourselves",
        ):
            self.assertIn(phrase, readme, f"README lost the brief phrase {phrase!r}")

    def test_readme_counts_match_the_shipped_database(self):
        """Doc numbers drift silently. Assert the headline counts against the data."""
        import json as _json
        import re as _re
        readme = pathlib.Path(ROOT, "README.md").read_text(encoding="utf-8")
        with open(os.path.join(DATA_DIR, "discrepancies.json"), encoding="utf-8") as fh:
            counts = _json.load(fh)["meta"]["counts"]
        n = counts["total_records"]
        self.assertIn(f"{n} official correction records", readme,
                      f"README does not state the current row count ({n})")
        self.assertIn(f"{n}-row verified seed", readme)
        self.assertNotIn("36-row verified seed", readme, "README still claims the old row count")
        self.assertNotIn("74-row verified seed", readme, "README still claims the old row count")
        self.assertEqual(
            counts["severity_3_high_priority_scoring_stat_or_scoreboard_candidate"], 0
        )
        s3 = counts["severity_3_high_priority_scoring_stat_or_scoreboard_candidate"]
        s2 = counts["severity_2_market_relevant_numeric"]
        s1 = counts["severity_1_relevant_but_small"]
        s0 = counts["severity_0_out_of_scope"]
        # The severity split is DERIVED from the shipped data, never hardcoded:
        # a hardcoded split is what let an earlier revision ship a README that
        # described a database it no longer had.
        self.assertEqual(s3 + s2 + s1 + s0, n, "severity buckets must partition the rows")
        self.assertIn(
            f"Not one of the {n} rows records a scoring-event change", readme,
            f"README does not state the current scoring-event count ({n})",
        )
        self.assertIn(f"{s3} / {s2} / {s1} / {s0}", readme,
                      "README does not state the current severity split")

    def test_readme_states_the_measured_date_gap_range(self):
        """The correction-latency range is measured, not asserted from memory."""
        import json as _json

        readme = pathlib.Path(ROOT, "README.md").read_text(encoding="utf-8")
        with open(os.path.join(DATA_DIR, "discrepancies.json"), encoding="utf-8") as fh:
            records = _json.load(fh)["records"]
        gaps = [r["days_from_game_to_correction"] for r in records
                if r["days_from_game_to_correction"] is not None]
        self.assertTrue(gaps)
        lo, hi = min(gaps), max(gaps)
        self.assertIn(f"{lo}–{hi} days", readme,
                      f"README does not state the measured gap range ({lo}–{hi} days)")


class TestFeed(unittest.TestCase):
    """
    The feed is what makes this usable day to day: it must record clean runs, not
    only alarms, or 'nothing changed' is indistinguishable from 'never ran'.
    """

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "feed.json")

    def tearDown(self):
        self.tmp.cleanup()

    def _report(self, n_alerts=0):
        """Build a report through the REAL diff path, not a hand-made stub."""
        import detect
        old = {"g1": make_row(home_score="24", result="4", total="44")}
        new = {"g1": make_row(home_score="24", result="4", total="44")}
        if n_alerts:
            new = {"g1": make_row(home_score="27", result="7", total="47")}
        changes = detect.diff_final_records(old, new, detect.FROZEN_FIELDS_GAMES)
        if n_alerts:
            self.assertGreater(len(changes), 0, "fixture must actually produce a change")
        return detect.build_alert_report(changes, source="test", min_severity=0)

    def test_clean_run_is_recorded_not_dropped(self):
        import feed
        f = feed.append_run(self._report(0), "old.csv", "new.csv", self.path)
        self.assertEqual(f["summary"]["runs_recorded"], 1)
        self.assertEqual(f["summary"]["runs_clean"], 1)
        self.assertEqual(f["latest"]["status"], "clean")
        self.assertEqual(f["latest"]["verification_status"], "no_change_detected")

    def test_alert_run_is_recorded_with_pending_confirmation(self):
        import feed
        f = feed.append_run(self._report(1), "old.csv", "new.csv", self.path)
        self.assertEqual(f["latest"]["status"], "ALERTS")
        # One game whose score, result and total all moved = 3 field-level alerts.
        self.assertEqual(f["latest"]["alerts_total"], 3)
        self.assertEqual(f["summary"]["runs_with_alerts"], 1)
        self.assertEqual(f["summary"]["total_alerts"], 3)
        self.assertEqual(
            f["latest"]["verification_status"],
            "detected_by_diff_pending_manual_confirmation",
        )
        # The machine never claims a realised outcome change.
        self.assertIsNone(f["latest"]["actually_changed_outcome"])

    def test_newest_run_is_first_and_history_is_capped(self):
        import feed
        for i in range(3):
            f = feed.append_run(self._report(0), f"old{i}.csv", f"new{i}.csv", self.path)
        self.assertEqual(f["summary"]["runs_recorded"], 3)
        self.assertEqual(f["runs"][0]["old_snapshot"], "old2.csv")
        self.assertEqual(f["summary"]["last_run"], f["runs"][0]["checked_at"])

    def test_rerunning_the_same_pair_does_not_duplicate(self):
        import feed
        feed.append_run(self._report(0), "a.csv", "b.csv", self.path)
        f = feed.append_run(self._report(0), "a.csv", "b.csv", self.path)
        self.assertEqual(f["summary"]["runs_recorded"], 1, "same snapshot pair double-counted")

    def test_identical_inputs_are_flagged_so_a_clean_run_is_interpretable(self):
        """A clean run whose two snapshots are the same bytes is a no-op, not a check."""
        import feed
        r = self._report(0)
        r["inputs"] = {"old": {"sha256": "aa"}, "new": {"sha256": "aa"}, "old_final_records": 5}
        f = feed.append_run(r, "a.csv", "b.csv", self.path)
        self.assertTrue(f["latest"]["identical_inputs"])

    def test_shipped_feed_is_well_formed(self):
        """The feed the site renders must exist and carry its honesty labels."""
        import json as _json
        p = os.path.join(DATA_DIR, "alerts", "feed.json")
        if not os.path.exists(p):
            self.skipTest("no feed recorded yet")
        with open(p, encoding="utf-8") as fh:
            d = _json.load(fh)
        for key in ("what_this_is", "what_a_recorded_alert_is", "what_a_clean_run_means"):
            self.assertIn(key, d["meta"], f"feed is missing its honesty label {key}")
        self.assertIn("runs", d)
        for run in d["runs"]:
            self.assertIn(run["status"], ("clean", "ALERTS"))
            self.assertIsNone(run["actually_changed_outcome"])


class TestShippedDatabase(unittest.TestCase):
    """Guards the shipped artefacts, including the 'no hallucination' contract."""

    DATA = os.path.join(os.path.dirname(HERE), "data")

    def _load(self, name):
        import json
        with open(os.path.join(self.DATA, name), encoding="utf-8") as f:
            return json.load(f)

    def test_database_identifies_the_exact_game_data_input_hash(self):
        db = self._load("discrepancies.json")
        source = db["meta"]["game_data_input"]
        import re
        self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")
        self.assertGreater(source["bytes"], 0)
        self.assertIn("third-party mirror", source["source"])
        self.assertTrue(source["source_url"].startswith("https://github.com/nflverse/nfldata/"))
        self.assertFalse(source["retained_by_builder"])
        self.assertIn("not inferred", source["note"])

    def test_every_record_has_a_reviewable_source_url(self):
        db = self._load("discrepancies.json")
        self.assertGreater(len(db["records"]), 0)
        for r in db["records"]:
            self.assertTrue(r["source_url_archived"].startswith("https://web.archive.org/"), r["record_id"])
            self.assertTrue(r["source_url_live_now_retired"].startswith("https://fantasy.nfl.com/"), r["record_id"])
            self.assertIn("NFL League Office", r["source_publisher"])
            self.assertIn("Elias", r["source_publisher"])

    def test_reason_unknown_is_explicit_and_not_inferred(self):
        db = self._load("discrepancies.json")
        for r in db["records"]:
            self.assertIsNone(r["correction_reason"], r["record_id"])
            self.assertEqual(
                r["correction_reason_status"],
                "not_stated_in_archived_official_notice",
                r["record_id"],
            )

    def test_date_gap_matches_source_row_dates(self):
        from datetime import datetime

        db = self._load("discrepancies.json")
        gaps = []
        for r in db["records"]:
            correction_date = parse_correction_date(r["correction_date_text"], r["season"])
            self.assertIsNotNone(correction_date, r["record_id"])
            if not r.get("game_date"):
                self.assertIsNone(r["days_from_game_to_correction"], r["record_id"])
                self.assertTrue(
                    any("TEAM_NOT_PRINTED" in flag for flag in r["review_flags"]),
                    r["record_id"],
                )
                continue
            game_date = datetime.strptime(r["game_date"], "%Y-%m-%d")
            gap = (correction_date - game_date).days
            self.assertEqual(gap, r["days_from_game_to_correction"], r["record_id"])
            gaps.append(gap)
        # DERIVED, not hardcoded. An earlier revision asserted exactly 70 gaps
        # spanning 1-4 days; expanding the database to 137 joined rows (max 6
        # days, from a Thursday-night game corrected the following Wednesday)
        # broke a number that was really just a snapshot of the data.
        joined = sum(1 for r in db["records"] if r.get("game_date"))
        self.assertEqual(len(gaps), joined)
        self.assertEqual(len(gaps), sum(1 for r in db["records"]
                                        if r["days_from_game_to_correction"] is not None))
        # Every joined gap must be non-negative and inside the project's
        # 14-day review window; those are real invariants, unlike the extremes.
        self.assertGreaterEqual(min(gaps), 0, "a correction dated before its game")
        self.assertLessEqual(max(gaps), 14, "a gap beyond the DATE_LATE review threshold")

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
        #
        # CONTRACT (tightened 2026-10-07): `team` is exactly what the official page
        # printed. On a defensive-unit row the page prints a franchise NICKNAME and
        # no code at all, so `team` is null there by design and `team_source` says
        # "derived_from_printed_nickname". Every other row must carry a real code.
        # Previously the raw layer silently normalised codes (JAC -> JAX), which
        # made this "as printed" field untrue.
        for r in db["records"]:
            self.assertIn("team_normalized", r, r["record_id"])
            self.assertIn("team_source", r, r["record_id"])
            if r["team"] in ("", None):
                self.assertIn(
                    r["team_source"],
                    ("derived_from_printed_nickname", "not_printed_on_source"),
                    f"{r['record_id']} has no as-printed code but claims {r['team_source']}",
                )
                if r["team_source"] == "derived_from_printed_nickname":
                    self.assertEqual(r["position"], "DEF", r["record_id"])
                else:
                    # A row with no team code must be flagged, never silently joined.
                    self.assertTrue(
                        any(f.startswith("TEAM_NOT_PRINTED") for f in r["review_flags"]),
                        f"{r['record_id']} has no team code but no TEAM_NOT_PRINTED flag",
                    )
                    self.assertIsNone(r.get("game_id"), r["record_id"])
            else:
                self.assertEqual(
                    r["team_source"], "as_printed_on_official_page", r["record_id"]
                )
            if r.get("game_id"):
                self.assertNotIn(r["team_normalized"], ("", None), r["record_id"])

        # And the 2015 Rams game itself must show STL on both sides of the join.
        for r in db["records"]:
            if r.get("game_id") == "2015_16_STL_SEA":
                self.assertIn("STL", (r["away_team"], r["home_team"]))
                break

    def test_score_integrity_study_is_limited_to_completed_mirror_comparisons(self):
        st = self._load(os.path.join("evidence", "score_integrity_study.json"))
        self.assertEqual(st["status"], "complete")
        self.assertGreater(st["totals"]["game_snapshots_examined"], 1000)
        self.assertEqual(st["totals"]["selected_baselines"], st["totals"]["baselines_fetched"])
        self.assertEqual(st["totals"]["baselines_failed"], 0)
        self.assertEqual(st["totals"]["frozen_field_changes_vs_current"], 0)
        self.assertIn("caveat", st)
        self.assertIn("third-party mirror", st["caveat"].lower())
        self.assertIn("does not establish", st["conclusion"])
        self.assertNotIn("effectively immutable", st["conclusion"])

    def test_failed_evidence_baseline_cannot_be_summarized_as_zero_revisions(self):
        summary = pipeline_run.summarize_evidence_baselines([
            {"baseline": "2023-12-03", "error": "network unavailable"},
            {
                "baseline": "2025-11-12",
                "final_at_baseline": 100,
                "frozen_field_changes_vs_current": 0,
            },
        ])
        self.assertEqual(summary["status"], "incomplete")
        self.assertEqual(summary["totals"]["baselines_failed"], 1)
        self.assertIn("INCOMPLETE", summary["conclusion"])
        self.assertIn("No conclusion about the unfetched baselines", summary["conclusion"])

    def test_market_sensitivity_is_line_distance_not_occurrence_or_settlement(self):
        ms = self._load("market_sensitivity_2025_2026.json")
        summary = ms["summary"]
        self.assertIn("Distance-based sensitivity screen only", summary["framing"])
        self.assertIn("does not mean a correction occurred", summary["framing"])
        self.assertIn("wager settled", summary["framing"])
        self.assertEqual(summary["games_considered_with_scores_and_lines"], 349)
        self.assertEqual(summary["games_within_distance_threshold_of_a_line"], 82)
        self.assertEqual(summary["zero_margin_line_distance_matches"], 10)
        self.assertGreater(summary["games_considered_with_scores_and_lines"], 0)
        source = summary["game_data_input"]
        self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")
        self.assertGreater(source["bytes"], 0)
        self.assertIn("third-party mirror", source["source"])
        self.assertFalse(source["retained_by_builder"])
        for game in ms["games"]:
            self.assertIn("margin_line_within_threshold", game)
            self.assertIn("zero_margin_line_distance", game)
            self.assertNotIn("pushed_on_spread", game)
            self.assertNotIn("min_correction_points_to_flip_spread", game)

    def test_market_sensitivity_does_not_infer_a_push_from_magnitude_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "games.csv")
            rows = [{
                "game_id": "sample-game",
                "season": "2025",
                "week": "1",
                "gameday": "2025-09-01",
                "away_team": "AAA",
                "home_team": "BBB",
                "away_score": "17",
                "home_score": "20",
                "spread_line": "-3",
                "total_line": "40.5",
            }]
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            games, summary = analyse_market_sensitivity(path, {2025}, threshold=1.0)

        self.assertEqual(summary["zero_margin_line_distance_matches"], 1)
        self.assertTrue(games[0]["zero_margin_line_distance"])
        self.assertNotIn("pushed_on_spread", games[0])
        self.assertIn("Spread sign/side", games[0]["note"])


    def test_every_case_card_on_the_site_resolves_to_a_real_record(self):
        """
        Regression guard for a bug shipped on 2026-10-07: the site selected its
        six case cards by record_id, which is a POSITIONAL ordinal assigned in
        build order. Adding 38 rows silently re-pointed every card at a different
        record. app.js now selects by natural key; this asserts each key still
        matches exactly one shipped record, so the guard survives future edits
        to either file.
        """
        import json as _json
        import re as _re

        app = pathlib.Path(ROOT, "docs", "app.js").read_text(encoding="utf-8")
        block = _re.search(r"const CASE_KEYS = \[(.*?)\];", app, _re.S)
        self.assertIsNotNone(block, "CASE_KEYS array not found in docs/app.js")
        keys = _re.findall(
            r"season:\s*(\d+),\s*week:\s*(\d+),\s*player:\s*'([^']+)',\s*"
            r"stat:\s*'([^']+)',\s*date:\s*'([^']+)'",
            block.group(1),
        )
        self.assertEqual(len(keys), 6, f"expected 6 case cards, parsed {len(keys)}")

        db = self._load("discrepancies.json")
        for season, week, player, stat, date in keys:
            matches = [
                r for r in db["records"]
                if str(r["season"]) == season and str(r["week"]) == week
                and r["player"] == player and r["stat"] == stat
                and r.get("correction_date_text") == date
            ]
            self.assertEqual(
                len(matches), 1,
                f"case card {player} / {stat} ({season} W{week}, {date}) matches "
                f"{len(matches)} records — it must match exactly one",
            )

    def test_attempt_ledger_records_attempts_and_survives_failures(self):
        """
        The feed records completed comparisons. If the schedule breaks, no new
        row appears and the page would keep showing the last success as current.
        Health records ATTEMPTS, so a dead monitor is visible.

        The critical property: a failure must NOT erase last_success — the page
        needs both "when it last worked" and "it is now broken".
        """
        import json as _json
        import tempfile

        import feed

        with tempfile.TemporaryDirectory() as td:
            hp = os.path.join(td, "attempts.json")

            fresh = feed.load_attempts(hp)
            self.assertEqual(fresh["status"], "unknown")
            self.assertIsNone(fresh["last_attempt"])

            ok = feed.record_attempt(hp, "ok", "first run")
            self.assertEqual(ok["status"], "ok")
            self.assertEqual(ok["consecutive_failures"], 0)
            first_success = ok["last_success"]

            bad = feed.record_attempt(hp, "failed", "upstream 500")
            self.assertEqual(bad["status"], "failed")
            self.assertEqual(bad["consecutive_failures"], 1)
            self.assertEqual(bad["last_success"], first_success,
                             "a failure must not erase the last success timestamp")
            self.assertIsNotNone(bad["last_failure"])

            bad2 = feed.record_attempt(hp, "failed", "still down")
            self.assertEqual(bad2["consecutive_failures"], 2)

            recovered = feed.record_attempt(hp, "ok", "back up")
            self.assertEqual(recovered["consecutive_failures"], 0)

            # A misspelled status must be rejected, not silently written: a
            # typo would otherwise read as "nothing wrong" on the page.
            with self.assertRaises(ValueError):
                feed.record_attempt(hp, "OK", "wrong case")

            # Baseline is neither success nor failure.
            base = feed.record_attempt(hp, "baseline", "first snapshot")
            self.assertEqual(base["status"], "baseline")
            self.assertEqual(base["consecutive_failures"], 0)

            on_disk = _json.loads(pathlib.Path(hp).read_text())
            self.assertEqual(on_disk["status"], "baseline")

    def test_attempt_age_is_computed_and_none_when_never_attempted(self):
        import datetime as _dt

        import feed

        now = _dt.datetime(2026, 10, 8, 3, 0, tzinfo=_dt.timezone.utc)
        self.assertIsNone(feed.attempt_age_hours({"last_attempt": None}, now=now))
        self.assertAlmostEqual(
            feed.attempt_age_hours({"last_attempt": "2026-10-08T00:00:00Z"}, now=now), 3.0
        )
        self.assertIsNone(feed.attempt_age_hours({"last_attempt": "not-a-date"}, now=now))

    def test_attempt_ledger_is_published_alongside_the_site(self):
        """An attempt ledger that never reaches docs/ renders nothing on the page."""
        src = os.path.join(DATA_DIR, "alerts", "attempts.json")
        dst = os.path.join(ROOT, "docs", "data", "alerts", "attempts.json")
        if not os.path.exists(src):
            self.skipTest("no attempt recorded yet")
        self.assertTrue(os.path.exists(dst), "run ./pipeline/sync_site_data.sh")
        with open(src, "rb") as a, open(dst, "rb") as b:
            self.assertEqual(a.read(), b.read(), "published attempt ledger has drifted from data/")

    def test_live_feed_is_published_alongside_the_site(self):
        """The site renders data/alerts/feed.json; it must be copied like the rest."""
        src = os.path.join(DATA_DIR, "alerts", "feed.json")
        dst = os.path.join(ROOT, "docs", "data", "alerts", "feed.json")
        if not os.path.exists(src):
            self.skipTest("no feed recorded yet")
        self.assertTrue(os.path.exists(dst), "run ./pipeline/sync_site_data.sh")
        with open(src, "rb") as a, open(dst, "rb") as b:
            self.assertEqual(a.read(), b.read(), "published feed has drifted from data/")


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

    def test_every_element_id_the_site_script_touches_exists_in_the_page(self):
        """
        BUG FOUND 2026-10-07 (this guard exists because of it).

        app.js referenced three IDs -- 'stat-snapshots-status',
        'integrity-callout' and 'zero-margin-count' -- that did not exist in
        index.html. `document.getElementById(x).textContent = ...` throws on
        null, the throw escaped into init()'s catch, and the catch blanked
        EVERY table on the page with "Could not load data". The page had been
        broken since the IDs were introduced, and the data tests could not see
        it because they only check data fields, not DOM ids.

        A missing label must never be able to take down the whole render.
        """
        import re as _re

        app = pathlib.Path(ROOT, "docs", "app.js").read_text(encoding="utf-8")
        html = pathlib.Path(ROOT, "docs", "index.html").read_text(encoding="utf-8")
        ids = set(_re.findall(r'id="([^"]+)"', html))

        refs = set(_re.findall(r"getElementById\(\s*['\"]([^'\"]+)['\"]", app))
        refs |= set(_re.findall(r"querySelector\(\s*['\"]#([A-Za-z0-9_-]+)", app))
        refs |= set(_re.findall(r"setText\(\s*['\"]([^'\"]+)['\"]", app))
        self.assertTrue(refs, "no element ids found in app.js — the scan is broken")

        missing = sorted(r for r in refs if r not in ids)
        self.assertEqual([], missing,
                         "app.js touches element ids that index.html does not define")

    def test_no_placeholder_on_the_page_is_left_unpopulated(self):
        """
        The reverse of the check above. `stat-snapshots-2` shipped as a literal
        "—" in the prose and nothing ever filled it in, so the page read
        "The study covers — game-snapshot comparisons". A placeholder that is
        never populated is worse than a missing one: it looks like data.
        """
        import re as _re

        app = pathlib.Path(ROOT, "docs", "app.js").read_text(encoding="utf-8")
        html = pathlib.Path(ROOT, "docs", "index.html").read_text(encoding="utf-8")
        refs = set(_re.findall(r"getElementById\(\s*['\"]([^'\"]+)['\"]", app))
        refs |= set(_re.findall(r"querySelector\(\s*['\"]#([A-Za-z0-9_-]+)", app))
        refs |= set(_re.findall(r"setText\(\s*['\"]([^'\"]+)['\"]", app))

        placeholders = _re.findall(
            r'<(\w+)[^>]*id="([A-Za-z0-9_-]+)"[^>]*>\s*\u2014\s*</\1>', html
        )
        self.assertTrue(placeholders, "no placeholder spans found — the scan is broken")
        unset = [i for _, i in placeholders if i not in refs]
        self.assertEqual([], unset, "index.html has placeholders app.js never fills in")

    def test_the_site_script_never_assigns_to_an_unchecked_element(self):
        """Direct `.textContent =` on getElementById is the pattern that broke the page."""
        import re as _re

        app = pathlib.Path(ROOT, "docs", "app.js").read_text(encoding="utf-8")
        # Skip comment lines: the setText docstring quotes the bad pattern on
        # purpose to explain why the helper exists.
        code = "\n".join(
            ln for ln in app.splitlines()
            if not ln.lstrip().startswith(("*", "//", "/*"))
        )
        bad = _re.findall(r"document\.getElementById\([^)]*\)\.textContent\s*=", code)
        self.assertEqual([], bad,
                         "use setText(id, value) — it degrades gracefully when the element "
                         "is absent instead of throwing and blanking the page")

    def test_the_site_does_not_count_missing_gaps_as_zero_day_corrections(self):
        """
        BUG FIXED 2026-10-07.

        The site computed its "days to correction" range as
            rows.map((r) => Number(r.days_from_game_to_correction)).filter(Number.isFinite)
        `Number(null) === 0`, which IS finite. The 4 rows that could not be joined
        to a game (the official page printed no team code for them) were therefore
        counted as 0-day corrections, and the headline figure read "0-6 days" when
        not one row in the database was corrected on the day of its game.

        Nulls must be dropped BEFORE the numeric cast, never after.
        """
        import re as _re

        app = pathlib.Path(ROOT, "docs", "app.js").read_text(encoding="utf-8")
        code = "\n".join(
            ln for ln in app.splitlines() if not ln.lstrip().startswith(("*", "//", "/*"))
        )
        bad = _re.findall(r"Number\(r\.days_from_game_to_correction\)", code)
        self.assertEqual([], bad, "cast before null-check; use gapValues(rows)")

        # And the headline range must equal the range of the non-null gaps in the
        # data, which is the property that was silently violated.
        import json as _json

        with open(os.path.join(DATA_DIR, "discrepancies.json"), encoding="utf-8") as fh:
            records = _json.load(fh)["records"]
        gaps = [r["days_from_game_to_correction"] for r in records
                if r["days_from_game_to_correction"] is not None]
        self.assertTrue(gaps)
        self.assertNotIn(0, gaps,
                         "a 0-day correction would be a same-day correction; verify it is real")
        self.assertEqual(min(gaps), 1)

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

    def test_review_flags_are_visible_in_the_site_database(self):
        import json
        import pathlib

        html = pathlib.Path(self.ROOT, "docs", "index.html").read_text(encoding="utf-8")
        app = pathlib.Path(self.ROOT, "docs", "app.js").read_text(encoding="utf-8")
        db = json.loads(pathlib.Path(self.ROOT, "data", "discrepancies.json").read_text(encoding="utf-8"))
        self.assertIn('class="no-sort">Review flags</th>', html)
        self.assertIn("r.review_flags", app)
        self.assertTrue(any(row["review_flags"] for row in db["records"]))
        self.assertTrue(any(
            "TEAM_NOT_PRINTED" in flag
            for row in db["records"] for flag in row["review_flags"]
        ))

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
