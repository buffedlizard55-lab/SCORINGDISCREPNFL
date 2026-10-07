import pathlib
import unittest
from datetime import datetime, timezone

from scripts.poll_official_corrections import (
    SourceError,
    classify_market,
    correction_id,
    correction_issue,
    correction_page_url,
    current_nfl_season,
    GitHubClient,
    parse_correction_html,
    seasons_to_poll,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class SeasonWindowTests(unittest.TestCase):
    def test_fall_selects_the_new_season(self):
        self.assertEqual(current_nfl_season(datetime(2026, 9, 1, tzinfo=timezone.utc)), 2026)

    def test_winter_and_offseason_select_the_most_recent_completed_season(self):
        for date in (datetime(2026, 1, 15, tzinfo=timezone.utc), datetime(2026, 8, 31, tzinfo=timezone.utc)):
            with self.subTest(date=date):
                self.assertEqual(current_nfl_season(date), 2025)

    def test_lookback_includes_the_base_and_prior_seasons(self):
        self.assertEqual(seasons_to_poll(2026, 2), [2026, 2025])


class CorrectionParserTests(unittest.TestCase):
    def test_parses_official_table_and_calculates_delta(self):
        url = "https://tab.fantasy.nfl.com/research/statcorrections?statSeason=2020&statWeek=7"
        rows = parse_correction_html(fixture("stat-corrections-sample.html"), 2020, 7, url)
        self.assertEqual(len(rows), 2)
        goff = rows[0]
        self.assertEqual(goff["player"], "Jared Goff")
        self.assertEqual(goff["position"], "QB")
        self.assertEqual(goff["team"], "LA")
        self.assertEqual(goff["stat"], "Passing Yards")
        self.assertEqual(goff["old_value"], 219)
        self.assertEqual(goff["new_value"], 220)
        self.assertEqual(goff["delta"], 1)
        self.assertEqual(goff["fantasy_points_delta"], 0.04)
        self.assertEqual(goff["market_classification"], "possible_player_or_team_market")
        self.assertEqual(len(goff["id"]), 20)

    def test_parses_q_injury_suffix_without_including_it_in_team(self):
        rows = parse_correction_html(
            fixture("stat-corrections-sample.html"),
            2020,
            7,
            "https://tab.fantasy.nfl.com/research/statcorrections",
        )
        self.assertEqual(rows[1]["player"], "Kyler Murray")
        self.assertEqual(rows[1]["team"], "ARI")
        self.assertEqual(rows[1]["position"], "QB")
        self.assertEqual(rows[1]["delta"], 1)

    def test_accepts_explicit_empty_state(self):
        rows = parse_correction_html(
            fixture("stat-corrections-empty.html"),
            2026,
            5,
            "https://tab.fantasy.nfl.com/research/statcorrections",
        )
        self.assertEqual(rows, [])

    def test_does_not_treat_redirect_page_as_zero_corrections(self):
        with self.assertRaises(SourceError):
            parse_correction_html(
                fixture("source-redirect.html"),
                2026,
                5,
                "https://tab.fantasy.nfl.com/research/statcorrections",
            )

    def test_rejects_unknown_stat_change_format(self):
        malformed = """<table><tr><th>Player</th><th>Date</th><th>Stat</th><th>Points</th></tr>
        <tr><td>Test Player QB - NYG</td><td>Oct 1</td><td>Yards revised to 42.</td><td>0.1</td></tr></table>"""
        with self.assertRaises(SourceError):
            parse_correction_html(malformed, 2026, 1, "https://tab.fantasy.nfl.com/research/statcorrections")

    def test_rejects_short_malformed_row_instead_of_silently_returning_zero(self):
        malformed = """<table><tr><th>Player</th><th>Date</th><th>Stat</th><th>Points</th></tr>
        <tr><td>Test Player QB - NYG</td><td>Oct 1</td><td>Passing Yards changed from 10 to 11.</td></tr></table>"""
        with self.assertRaisesRegex(SourceError, "expected 4"):
            parse_correction_html(malformed, 2026, 1, "https://tab.fantasy.nfl.com/research/statcorrections")

    def test_header_only_page_requires_an_explicit_empty_state(self):
        header_only = "<table><tr><th>Player</th><th>Date</th><th>Stat</th><th>Points</th></tr></table>"
        with self.assertRaisesRegex(SourceError, "no correction rows"):
            parse_correction_html(header_only, 2026, 1, "https://tab.fantasy.nfl.com/research/statcorrections")

    def test_ignores_unrelated_footer_table_after_corrections(self):
        html = fixture("stat-corrections-sample.html").replace(
            "</body>", "<table><tr><td>Footer</td><td>text</td></tr></table></body>"
        )
        rows = parse_correction_html(html, 2020, 7, "https://tab.fantasy.nfl.com/research/statcorrections")
        self.assertEqual(len(rows), 2)

    def test_correction_url_preserves_existing_filters(self):
        url = correction_page_url(
            "https://tab.fantasy.nfl.com/research/statcorrections?position=1",
            2026,
            5,
        )
        self.assertIn("position=1", url)
        self.assertIn("statSeason=2026", url)
        self.assertIn("statWeek=5", url)
        self.assertIn("statType=weekStats", url)

    def test_id_is_deterministic(self):
        row = {"season": 2026, "week": 5, "player": "Example", "position": "QB", "team": "NYG", "date": "Oct 1", "stat": "Passing Yards", "old_value": 10, "new_value": 11}
        self.assertEqual(correction_id(row), correction_id(row.copy()))

    def test_issue_is_explicitly_a_candidate_not_a_market_claim(self):
        row = {
            "id": "0123456789abcdefabcd",
            "season": 2026,
            "week": 5,
            "player": "Example Player",
            "position": "QB",
            "team": "NYG",
            "date": "Oct 1",
            "stat": "Passing Yards",
            "old_value": 10,
            "new_value": 11,
            "delta": 1,
            "fantasy_points_delta": 0.04,
            "source_url": "https://tab.fantasy.nfl.com/research/statcorrections",
            "market_classification": "possible_player_or_team_market",
        }
        title, body = correction_issue(row)
        self.assertIn("NFL stat correction", title)
        self.assertIn("manual review required", body)
        self.assertIn("has **not** checked sportsbook lines", body)
        self.assertIn("<!-- nfl-correction:0123456789abcdefabcd -->", body)

    def test_github_issue_listing_paginates_and_excludes_pull_requests(self):
        client = object.__new__(GitHubClient)
        responses = [
            [{"number": 1}, *[{"number": n + 2, "pull_request": {"url": f"https://api.github.com/pulls/{n + 2}"}} for n in range(99)]],
            [{"number": 101}],
        ]
        calls = []

        def fake_request(method, path):
            calls.append((method, path))
            return responses.pop(0)

        client.request_json = fake_request
        issues = client.list_issues("official-stat-correction")
        self.assertEqual([issue["number"] for issue in issues], [1, 101])
        self.assertEqual(len(calls), 2)

    def test_market_classification_covers_idp_stats(self):
        self.assertEqual(classify_market("Assisted Tackles"), "possible_player_or_team_market")
        self.assertEqual(classify_market("Games Played"), "fantasy_or_roster_only_unless_a_market_is_listed")
        self.assertEqual(classify_market("Unknown Metric"), "unclassified_stat_change_review_required")


if __name__ == "__main__":
    unittest.main()
