import csv
import io
import json
import sqlite3
import unittest
from scripts.build import ROOT, build, validate
from scripts.monitor import KEYS, STATS, ingest, parse


def fixture(value='199', extra=None):
    row = dict.fromkeys(KEYS, 'x') | dict.fromkeys(STATS, '0')
    row['rushing_yards'] = value
    row.update(extra or {})
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=KEYS+STATS)
    w.writeheader(); w.writerow(row)
    return s.getvalue().encode()


class ProjectTests(unittest.TestCase):
    def test_evidence(self):
        validate(json.loads((ROOT/'data/events.json').read_text()), json.loads((ROOT/'data/sources.json').read_text()))

    def test_re_reviewed_cases_keep_material_caveats(self):
        data = json.loads((ROOT/'data/events.json').read_text())
        records = {event['id']: event for event in data['events']}
        expected = {
            '2008-09-08-den-oak',
            '2010-10-24-buf-bal',
            '2011-09-19-ram-nyg',
            '2015-11-01-nyg-no',
            '2018-12-16-dal-ind',
        }
        self.assertTrue(expected.issubset(records))
        self.assertIn('299', ' '.join(records['2008-09-08-den-oak']['flags']))
        self.assertIn('373', ' '.join(records['2010-10-24-buf-bal']['flags']))
        self.assertIn('504', ' '.join(records['2015-11-01-nyg-no']['flags']))
        elliott = records['2018-12-16-dal-ind']
        fumble = next(change for change in elliott['changes'] if change['stat'] == 'Fumbles (game total)')
        self.assertEqual((fumble['before'], fumble['after'], fumble['delta']), (1, 1, 0))
        self.assertIn('not removed', ' '.join(elliott['flags']).lower())
        for case_id in expected:
            self.assertEqual(records[case_id]['settlement'], 'No sportsbook settlement independently verified')

    def test_deterministic_build(self):
        build(); before = (ROOT/'research-seed/index.html').read_bytes(); build()
        self.assertEqual(before, (ROOT/'research-seed/index.html').read_bytes())
        self.assertNotIn(b'<!-- CASES -->', before)
        self.assertEqual(before.count(b'<article '), 12)

    def test_baseline_repeat_and_change(self):
        with sqlite3.connect(':memory:') as db:
            self.assertTrue(ingest(db, fixture(), 'test')['baseline'])
            self.assertEqual(ingest(db, fixture(), 'test')['changes'], [])
            report = ingest(db, fixture('201'), 'test')
            self.assertEqual(report['changes'][0]['delta'], 2)
            self.assertEqual(ingest(db, fixture(), 'other')['changes'], [])

    def test_null_not_zero(self):
        with sqlite3.connect(':memory:') as db:
            ingest(db, fixture(''), 'test')
            self.assertIsNone(ingest(db, fixture('0'), 'test')['changes'][0]['delta'])

    def test_fractional_sacks(self):
        self.assertEqual(next(iter(parse(fixture(extra={'def_sacks': '0.5'})).values()))['def_sacks'], .5)

    def test_bad_inputs(self):
        for raw in (b'', b'<html>News</html>', fixture('NaN'), fixture('Infinity'), fixture('bad')):
            with self.assertRaises(ValueError): parse(raw)

    def test_add_remove_not_zero_correction(self):
        with sqlite3.connect(':memory:') as db:
            ingest(db, fixture(), 'test')
            r = ingest(db, fixture(extra={'player_id':'new'}), 'test')
            self.assertEqual(r['changes'], [])
            self.assertEqual(len(r['added']), 1); self.assertEqual(len(r['removed']), 1)

    def test_failure_preserves_baseline(self):
        with sqlite3.connect(':memory:') as db:
            ingest(db, fixture(), 'test')
            with self.assertRaises(ValueError): ingest(db, b'broken', 'test')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM snapshots').fetchone()[0], 1)
