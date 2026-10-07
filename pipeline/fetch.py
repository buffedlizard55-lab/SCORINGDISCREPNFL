"""
fetch.py — Source adapters.

Every source here was manually reachable and verified during the initial
investigation. Each adapter records WHAT it fetched, WHEN, and a SHA-256 of the
bytes, so that any claim downstream is reproducible from a hash + URL.

VERIFIED STATUS OF EACH SOURCE (checked 2026-10-07, see LIMITATIONS.md):

  nfldata_games        LIVE.  nflverse/nfldata commits data/games.csv to git
                       every ~30 min during the season. Full git history at
                       codeload.github.com => we can snapshot any point in time.
                       This is the workhorse source.

  nflverse_release     BLOCKED IN SOME SANDBOXES. Release assets redirect to
                       release-assets.githubusercontent.com. Works on GitHub
                       Actions runners; did NOT work inside the restricted
                       evaluation sandbox. Kept because Actions is the real
                       deployment target.

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


def nfldata_snapshot_from_commit(sha: str, member: str = NFLDATA_CSV) -> bytes:
    """
    Download a full repo tarball at a specific commit and extract one file.

    We use codeload tarballs rather than the Contents API because games.csv is
    ~2.1 MB, above the Contents API's 1 MB inline limit. codeload serves the
    whole tree as tar.gz and is reachable wherever github.com is.
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
CDX_API = "http://web.archive.org/cdx/search/cdx"


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


def official_corrections_page(timestamp: str, original_url: str) -> bytes:
    """
    Fetch the raw archived HTML of an official corrections page.

    The `id_` modifier returns the ORIGINAL bytes without Wayback's injected
    banner/toolbar, which keeps parsing deterministic.
    """
    url = f"http://web.archive.org/web/{timestamp}id_/{original_url}"
    return http_get(url, timeout=120)


def official_corrections_url(season: int, week: int, position: str = "O") -> str:
    return (
        "https://fantasy.nfl.com/research/statcorrections"
        f"?position={position}&sort=pts&statCategory=stats"
        f"&statSeason={season}&statType=weekStats&statWeek={week}"
    )


# ---------------------------------------------------------------------------
# Source 3 — nflverse release assets (works on Actions, blocked in the
#            restricted sandbox; kept so the deployment target is real)
# ---------------------------------------------------------------------------
def nflverse_release_assets(repo: str, tag: str) -> list[dict]:
    url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    return http_json(url).get("assets", [])


def nflverse_pbp_asset_index(season: int) -> list[dict]:
    """
    Raw play-by-play, one asset per game. This is the dataset nflverse itself
    refreshes weekly specifically "to incorporate stat corrections during the
    week" (nflverse-pbp-internal/.github/workflows/refresh_raw_pbp.yaml, cron
    '0 2 * 1,2,9-12 3' = Wednesdays 02:00 UTC). Diffing two vintages of these
    assets is the highest-resolution correction detector available.
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


def write_snapshot(root: str, source: str, name: str, data: bytes, meta: dict | None = None) -> str:
    """Persist raw bytes + a manifest carrying the SHA-256 of exactly those bytes."""
    import hashlib

    d = snapshot_dir(root, source)
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
