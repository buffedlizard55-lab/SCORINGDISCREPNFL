"""Local normalized CSV snapshot detector. Candidates are NOT official corrections."""
import argparse
import csv
import hashlib
import io
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

KEYS = ('season', 'season_type', 'week', 'team', 'opponent_team', 'player_id')
STATS = ('passing_yards', 'passing_tds', 'passing_interceptions', 'rushing_yards',
         'rushing_tds', 'receptions', 'receiving_yards', 'receiving_tds',
         'def_sacks', 'def_interceptions', 'fg_made', 'pat_made',
         'passing_2pt_conversions', 'rushing_2pt_conversions', 'receiving_2pt_conversions')


def parse(raw):
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    if not set(KEYS + STATS).issubset(reader.fieldnames or []):
        raise ValueError('Missing required schema columns; refusing snapshot')
    result = {}
    for row in reader:
        if None in row or any(not row.get(k) for k in KEYS):
            raise ValueError('Malformed row or missing identity')
        key = '|'.join(row[k] for k in KEYS)
        if key in result:
            raise ValueError('Duplicate identity')
        values = {}
        for stat in STATS:
            v = row.get(stat)
            if v is None:
                raise ValueError('Truncated row')
            value = None if v.strip() in ('', 'NA') else float(v)
            if value is not None and not math.isfinite(value):
                raise ValueError('Nonfinite number')
            values[stat] = value
        result[key] = values
    if not result:
        raise ValueError('Empty feed is not a healthy snapshot')
    return result


def compare(old, new):
    changes = []
    for key in sorted(old.keys() & new.keys()):
        for stat in STATS:
            a, b = old[key][stat], new[key][stat]
            if a != b:
                changes.append(dict(key=key, stat=stat, before=a, after=b,
                                    delta=None if a is None or b is None else b-a,
                                    status='missing-value review' if a is None or b is None else 'unconfirmed provider change'))
    return dict(changes=changes, added=sorted(new.keys()-old.keys()), removed=sorted(old.keys()-new.keys()))


def ingest(db, raw, source):
    new = parse(raw)
    digest = hashlib.sha256(raw).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    db.execute('CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY, source TEXT, observed TEXT, hash TEXT, raw BLOB, normalized TEXT)')
    previous = db.execute('SELECT id, normalized FROM snapshots WHERE source=? ORDER BY id DESC LIMIT 1', (source,)).fetchone()
    report = compare(json.loads(previous[1]), new) if previous else dict(changes=[], added=[], removed=[])
    report.update(source=source, observed_at=now, sha256=digest, baseline=previous is None, previous_snapshot=previous[0] if previous else None)
    with db:
        cursor = db.execute('INSERT INTO snapshots(source, observed, hash, raw, normalized) VALUES(?,?,?,?,?)', (source, now, digest, raw, json.dumps(new)))
        report['snapshot_id'] = cursor.lastrowid
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('csv', type=Path)
    ap.add_argument('--source', required=True, help='Stable feed identity including season; never mix sources')
    ap.add_argument('--db', default='.monitor/snapshots.sqlite')
    args = ap.parse_args()
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.db) as db:
        print(json.dumps(ingest(db, args.csv.read_bytes(), args.source), indent=2))
