"""
fetch.py — Source adapters and snapshot helpers.

Sources were investigated and their access limits are recorded below; not
all endpoints were reachable from this sandbox. Fetch helpers return bytes or
metadata. `write_snapshot()` records bytes, SHA-256 and supplied metadata when
called, but fetch functions do not automatically persist a retrieval log.

ACCESS / EVIDENCE STATUS (checked 2026-10-07, see LIMITATIONS.md):

  nfldata_games        VERSIONED THIRD-PARTY MIRROR. A small sample of recent
                       commits to nflverse/nfldata data/games.csv inspected on
                       2026-10-07 was spaced roughly 15–30 minutes apart. This
                       is an observation, not a freshness guarantee or SLA.
                       Git history provides selected historical vintages.

  nflverse_release     METADATA ACCESSIBLE; ASSET BYTES NOT VERIFIED HERE.
                       Release assets redirect to
                       release-assets.githubusercontent.com, which was not
                       reachable from this sandbox. Access on another runner
                       must be tested; it is not assumed.

  official_corrections RETIRED BUT ARCHIVED. fantasy.nfl.com/research/
                       statcorrections now 302-redirects to nfl.com/news/
                       series/fantasy. Archived snapshots 2010-2025 remain on
                       the Wayback Machine and contain the authoritative
                       from->to correction rows published by the NFL League
                       Office + Elias Sports Bureau.

  espn_statcorrections LIVE BUT JS-RENDERED. fantasy.espn.com/football/
                       statcorrections renders client-side; there is no
                       documented public JSON endpoint. Not machine-parsable
                       without reverse engineering a private API. Flagged, not
                       relied upon.
"""

from __future__ import annotations

import gzip
import io
import json
import os
import tarfile
import urllib.parse
import urllib.request

UA = "SCORINGDISCREPNFL/1.0 (research; +https://github.com/buffedlizard55-lab/SCORINGDISCREPNFL)"


def http_get(url: str, timeout: int = 60, gunzip: bool = False) -> bytes:
    """
    Fetch bytes.

    NOTE (bug fixed during review): this used to transparently gunzip any body
    that began with the gzip magic bytes. That silently broke every *.tar.gz
    consumer, because codeload tarballs start with magic bytes and were being
    decompressed before tarfile ever saw them — tarfile then reported
    "not a gzip file (b'pa')", the 'pa' being the start of the
    'pax_global_header' tar member. Decompression is now opt-in and explicit.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    if gunzip and data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return data


def http_json(url: str, timeout: int = 60):
    return json.loads(http_get(url, timeout=timeout).decode("utf-8", "replace"))


# ---------------------------------------------------------------------------
# Source 1 — nflverse/nfldata (git-committed, versioned)
# ---------------------------------------------------------------------------
NFLDATA_REPO = "nflverse/nfldata"
NFLDATA_CSV = "data/games.csv"
NFLDATA_RAW_API = f"https://api.github.com/repos/{NFLDATA_REPO}/contents/{NFLDATA_CSV}"


def nfldata_commits(path: str = NFLDATA_CSV, limit: int = 20, until: str | None = None) -> list[dict]:
    """List commits touching a path, newest first. `until` is ISO-8601 UTC."""
    url = (
        f"https://api.github.com/repos/{NFLDATA_REPO}/commits"
        f"?path={urllib.parse.quote(path)}&per_page={limit}"
    )
    if until:
        url += f"&until={urllib.parse.quote(until)}"
    return http_json(url)


def nfldata_head_commit(path: str = NFLDATA_CSV, ref: str = "master") -> dict | None:
    """The newest commit touching `path`: our SOURCE WATERMARK.

    Why this matters: a snapshot's bytes tell you what the mirror said, but not
    how old that statement is. Recording the commit SHA and its date with every
    snapshot lets `pipeline/health.py` report source freshness independently of
    whether our own workflow ran, and lets any reviewer re-download exactly the
    vintage we snapshotted from codeload.

    Returns None rather than raising: an unreachable API must degrade the
    watermark to "unknown", never fake a value.
    """
    try:
        commits = nfldata_commits(path=path, limit=1)
    except Exception:
        return None
    if not commits:
        return None
    c = commits[0]
    return {
        "sha": c.get("sha"),
        "date": (c.get("commit", {}).get("committer", {}) or {}).get("date"),
        "message": ((c.get("commit", {}).get("message") or "").splitlines() or [""])[0][:120],
        "url": c.get("html_url"),
        "ref": ref,
    }


def nfldata_snapshot_from_commit(sha: str, member: str = NFLDATA_CSV) -> bytes:
    """
    Download a full repo tarball at a specific commit and extract one file.

    We use codeload tarballs rather than the Contents API because games.csv is
    ~2.1 MB, above the Contents API's 1 MB inline limit. codeload serves the
    whole tree as tar.gz; connectivity still depends on the caller's network.
    """
    url = f"https://codeload.github.com/{NFLDATA_REPO}/tar.gz/{sha}"
    blob = http_get(url, timeout=180)
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        for m in tf.getmembers():
            if m.name.endswith("/" + member) or m.name == member:
                f = tf.extractfile(m)
                if f is None:
                    raise RuntimeError(f"{member} is not a regular file in {sha}")
                return f.read()
    raise FileNotFoundError(f"{member} not found in tarball for {sha}")


def nfldata_snapshot_head(member: str = NFLDATA_CSV, ref: str = "master") -> bytes:
    url = f"https://codeload.github.com/{NFLDATA_REPO}/tar.gz/refs/heads/{ref}"
    blob = http_get(url, timeout=180)
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        for m in tf.getmembers():
            if m.name.endswith("/" + member) or m.name == member:
                f = tf.extractfile(m)
                if f is None:
                    continue
                return f.read()
    raise FileNotFoundError(member)


# ---------------------------------------------------------------------------
# Source 2 — Wayback Machine: archived official NFL stat-corrections pages
# ---------------------------------------------------------------------------
CDX_API = "https://web.archive.org/cdx/search/cdx"


def official_corrections_snapshots(season: int | None = None, limit: int = 200) -> list[tuple[str, str]]:
    """
    Return [(timestamp, original_url)] for archived official stat-corrections
    pages, optionally filtered to a season.
    """
    params = {
        "url": "fantasy.nfl.com/research/statcorrections",
        "matchType": "prefix",
        "collapse": "urlkey",
        "fl": "timestamp,original,statuscode",
        "limit": str(limit),
    }
    if season is not None:
        params["filter"] = f"original:.*statSeason={season}.*"
    url = CDX_API + "?" + urllib.parse.urlencode(params)
    raw = http_get(url, timeout=90).decode("utf-8", "replace")
    out = []
    for line in raw.splitlines():
        parts = line.split(" ")
        if len(parts) >= 2:
            out.append((parts[0], parts[1]))
    return out


def official_corrections_snapshot_url(timestamp: str, original_url: str) -> str:
    """Return the human-reviewable Wayback URL for a captured correction page."""
    return f"https://web.archive.org/web/{timestamp}/{original_url}"


def official_corrections_page(timestamp: str, original_url: str) -> bytes:
    """
    Fetch the raw archived HTML of an official corrections page.

    The `id_` modifier returns the ORIGINAL bytes without Wayback's injected
    banner/toolbar, which keeps parsing deterministic. Parsed rows should still
    store `official_corrections_snapshot_url()` for human review.
    """
    url = f"https://web.archive.org/web/{timestamp}id_/{original_url}"
    return http_get(url, timeout=120)


def official_corrections_url(season: int, week: int, position: str = "O") -> str:
    return (
        "https://fantasy.nfl.com/research/statcorrections"
        f"?position={position}&sort=pts&statCategory=stats"
        f"&statSeason={season}&statType=weekStats&statWeek={week}"
    )


# ---------------------------------------------------------------------------
# Source 3 — nflverse release metadata and assets (bytes not yet validated)
# ---------------------------------------------------------------------------
def nflverse_release_assets(repo: str, tag: str) -> list[dict]:
    url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    return http_json(url).get("assets", [])


def nflverse_pbp_asset_index(season: int) -> list[dict]:
    """Return release asset metadata for a season's raw play-by-play.

    The upstream repository documents a weekly refresh to incorporate stat
    corrections (see https://github.com/nflverse/nflverse-pbp/blob/master/.github/workflows/refresh_raw_pbp.yaml).
    A release listing does not prove a correction occurred or identify an
    official ruling. Asset bytes, schema, and a useful historical diff have not
    been validated in this project; see LIMITATIONS.md §3.
    """
    return nflverse_release_assets("nflverse/nflverse-pbp", f"raw_pbp_{season}")


def download_release_asset(url: str, timeout: int = 120) -> bytes:
    return http_get(url, timeout=timeout)


# ---------------------------------------------------------------------------
# Local snapshot store
# ---------------------------------------------------------------------------
def snapshot_dir(root: str, source: str, stamp: str | None = None) -> str:
    from datetime import datetime, timezone

    stamp = stamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    return os.path.join(root, "snapshots", source, stamp)


def write_snapshot(
    root: str,
    source: str,
    name: str,
    data: bytes,
    meta: dict | None = None,
    stamp: str | None = None,
) -> str:
    """
    Persist raw bytes + a manifest carrying the SHA-256 of exactly those bytes.

    `stamp` lets a caller label the snapshot with the vintage it actually
    represents (for example the upstream commit date) instead of wall-clock
    now. That matters for backfills: a snapshot labelled with today's clock
    time while holding bytes from 2026-09-22 would silently misdate the
    comparison window recorded in the feed.
    """
    import hashlib

    d = snapshot_dir(root, source, stamp=stamp)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    with open(path, "wb") as f:
        f.write(data)
    manifest_path = os.path.join(d, f"{name}.manifest.json")
    manifest = {
        "source": source,
        "file": name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        **(meta or {}),
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return path
