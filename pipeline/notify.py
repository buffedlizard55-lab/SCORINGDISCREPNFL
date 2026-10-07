"""
notify.py — delivery orchestration for alerts: idempotency, retry, receipts.

WHY THIS EXISTS
---------------
`detect.notify_webhook()` performs one HTTP POST. That is a transport, not a
notification system. A notification system has to answer four questions a single
POST cannot:

  1. Did we already send this?      -> idempotency key + delivery log
  2. Did it actually arrive?        -> a receipt with the HTTP status recorded
  3. What happened when it failed?  -> bounded retries, then a dead-letter entry
  4. Can a human audit it later?    -> an append-only, published receipt log

Without receipts, "the alert was sent" is an assumption. Without idempotency, a
retried workflow re-notifies people about the same comparison. Without a
dead-letter, a failing webhook looks identical to a quiet week.

HONESTY RULES
-------------
* The webhook URL is NEVER written to the log. Only the host (so the channel
  type is auditable) and a SHA-256 of the full URL (so a reader can confirm
  which configured endpoint was used without us publishing a secret).
* A receipt records what the endpoint told us. A 2xx is evidence the endpoint
  accepted the payload; it is NOT evidence a human read it. Slack/Discord
  webhooks give no read receipts and this module does not pretend otherwise.
* Delivery is at-least-once, not exactly-once: an endpoint can accept a message
  and lose the response, so a retry can duplicate. The idempotency key is
  included in the log so duplicates are detectable after the fact.
* A skipped or suppressed delivery is still recorded. Silence must be
  distinguishable from success.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import pathlib
import time
from urllib.parse import urlparse

import detect

MAX_ENTRIES = 200

# Bounded backoff. Retrying forever inside a CI job is worse than failing loudly:
# the job has a wall-clock limit, and a dead-letter entry is more useful than a
# hang. These are project choices, not a protocol requirement.
BACKOFF_SECONDS = (2, 8, 30)

OUTCOMES = (
    "delivered",            # endpoint returned 2xx
    "failed",               # endpoint returned non-2xx or the request errored
    "skipped_no_alerts",    # nothing to notify about; recorded so silence is auditable
    "suppressed_duplicate", # same idempotency key already delivered
    "not_configured",       # no webhook URL configured; report stays in the feed/artefact
)

META = {
    "what_this_is": (
        "Append-only log of alert delivery attempts. Every attempt is recorded, "
        "including skipped, suppressed and failed ones, so 'nobody was notified' "
        "is distinguishable from 'notification was not attempted'."
    ),
    "what_a_receipt_proves": (
        "Only that the configured endpoint returned an HTTP status. A 2xx means the "
        "endpoint accepted the payload; it is not a read receipt and not proof a "
        "human saw the alert."
    ),
    "privacy": (
        "The webhook URL is never stored. Only the host and a SHA-256 of the URL are "
        "recorded, so a channel can be audited without publishing a secret."
    ),
    "delivery_semantics": "at-least-once; a retry after a lost response can duplicate a message",
}


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def idempotency_key(report: dict) -> str:
    """Stable identity for *this comparison*, not for this run of the program.

    Deliberately excludes `generated_at` and `retrieved_at`: re-running the same
    snapshot pair minutes later must produce the same key, otherwise every retry
    looks like a new alert and people get notified twice for one change.
    """
    inputs = report.get("inputs", {}) or {}
    parts = [
        str(inputs.get("old", {}).get("sha256") or ""),
        str(inputs.get("new", {}).get("sha256") or ""),
        str(report.get("min_severity")),
        str(report.get("source") or ""),
    ]
    parts += sorted(str(a.get("alert_id")) for a in report.get("alerts", []) or [])
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]


def channel_of(url: str) -> tuple[str, str]:
    """Return (channel_name, host). The host is safe to publish; the token is not."""
    host = (urlparse(url).hostname or "").lower()
    if host in ("discord.com", "discordapp.com"):
        return "discord", host
    if host.endswith("slack.com"):
        return "slack", host
    return "generic_webhook", host


def load_log(path: str | os.PathLike) -> dict:
    p = pathlib.Path(path)
    if not p.exists():
        return {"meta": META, "deliveries": [], "summary": _summarize([])}
    data = json.loads(p.read_text(encoding="utf-8"))
    data.setdefault("meta", META)
    data.setdefault("deliveries", [])
    data["summary"] = _summarize(data["deliveries"])
    return data


def _summarize(deliveries: list[dict]) -> dict:
    by_outcome: dict[str, int] = {}
    for d in deliveries:
        by_outcome[d["outcome"]] = by_outcome.get(d["outcome"], 0) + 1
    dead = [d for d in deliveries if d.get("dead_letter")]
    return {
        "attempts_recorded": len(deliveries),
        "by_outcome": by_outcome,
        "delivered": by_outcome.get("delivered", 0),
        "failed": by_outcome.get("failed", 0),
        "dead_letter": len(dead),
        "last_delivery_attempt": deliveries[0]["attempted_at"] if deliveries else None,
        "last_dead_letter": dead[0]["attempted_at"] if dead else None,
    }


def find_by_key(log: dict, key: str) -> dict | None:
    for d in log.get("deliveries", []):
        if d.get("idempotency_key") == key:
            return d
    return None


def record_receipt(receipt: dict, path: str | os.PathLike) -> dict:
    """Prepend a receipt, cap history, rewrite the summary, persist."""
    log = load_log(path)
    log["meta"] = META
    log["deliveries"] = ([receipt] + log["deliveries"])[:MAX_ENTRIES]
    log["summary"] = _summarize(log["deliveries"])
    log["generated_at"] = _now()
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text(
        json.dumps(log, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return log


def deliver(report: dict, url: str | None, log_path: str | os.PathLike,
            max_attempts: int = 3, force: bool = False,
            poster=None, sleeper=None) -> dict:
    """Attempt delivery with idempotency, bounded retry and a persisted receipt.

    Never raises for transport problems: a failing webhook must produce a
    dead-letter receipt and a non-zero return, not a stack trace that hides the
    alert report already written to disk.

    `poster` and `sleeper` are resolved at CALL time rather than bound as default
    arguments. Binding `poster=detect.notify_webhook` in the signature captured
    the function object at import time, which silently defeated every
    `patch.object(detect, "notify_webhook", ...)` in the tests and sent real
    HTTPS requests to a third-party host during a unit-test run. Found because
    the suite hung instead of failing.
    """
    poster = poster or detect.notify_webhook
    sleeper = sleeper or time.sleep
    key = idempotency_key(report)
    receipt: dict = {
        "delivery_id": f"{key}-{_now().replace(':', '').replace('-', '')}",
        "idempotency_key": key,
        "attempted_at": _now(),
        "alert_count": int(report.get("total_alerts", 0)),
        "report_digest": hashlib.sha256(
            detect.render_markdown(report).encode("utf-8")).hexdigest()[:16],
        "review_url": report.get("review_url"),
        "attempts": 0,
        "outcome": None,
        "detail": None,
        "dead_letter": False,
    }

    if not url:
        receipt.update(outcome="not_configured",
                       detail="no webhook URL configured; report remains in the feed and artefact")
        record_receipt(receipt, log_path)
        return receipt

    channel, host = channel_of(url)
    receipt["channel"] = channel
    receipt["channel_host"] = host
    receipt["url_sha256"] = hashlib.sha256(url.encode("utf-8")).hexdigest()

    log = load_log(log_path)
    prior = find_by_key(log, key)
    if prior and prior.get("outcome") == "delivered" and not force:
        receipt.update(outcome="suppressed_duplicate",
                       detail=f"already delivered at {prior.get('attempted_at')} (delivery_id {prior.get('delivery_id')})")
        record_receipt(receipt, log_path)
        return receipt

    if report.get("total_alerts", 0) == 0:
        receipt.update(outcome="skipped_no_alerts", detail="clean comparison; nothing to notify")
        record_receipt(receipt, log_path)
        return receipt

    last_detail = None
    for attempt in range(1, max_attempts + 1):
        receipt["attempts"] = attempt
        try:
            ok, message = poster(report, url)
        except Exception as e:  # transport failure is data, not a crash
            ok, message = False, f"{type(e).__name__}: {e}"
        last_detail = message
        if ok:
            receipt.update(outcome="delivered", detail=message, dead_letter=False)
            record_receipt(receipt, log_path)
            return receipt
        if attempt < max_attempts:
            sleeper(BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)])

    receipt.update(outcome="failed", detail=last_detail, dead_letter=True)
    record_receipt(receipt, log_path)
    return receipt
