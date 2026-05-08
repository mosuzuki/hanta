#!/usr/bin/env python3
"""Fetch source pages and update lightweight dashboard metadata.

This script is intentionally conservative. It records source fetch status and
refresh time, but it does not blindly overwrite official case counts when
sources conflict. Use data/incident.json as the reviewed truth layer.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parents[1]
INCIDENT_PATH = ROOT / "data" / "incident.json"
SOURCES_PATH = ROOT / "data" / "sources.json"
FETCH_LOG_PATH = ROOT / "data" / "fetch_log.json"

USE_OPENAI_SUMMARY = False


def fetch_url(url: str, timeout: int = 30) -> tuple[int | None, str]:
    req = Request(
        url,
        headers={
            "User-Agent": "hantavirus-risk-dashboard/0.1 (+https://github.com/)"
        },
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read()
            return response.status, raw.decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError) as exc:
        return None, f"FETCH_ERROR: {exc}"


def strip_html(text: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_signals(source_id: str, text: str) -> dict[str, object]:
    """Extract non-authoritative signals for human review."""
    clean = strip_html(text)
    result: dict[str, object] = {"source_id": source_id, "matched": {}}
    patterns = {
        "cases_7": r"seven cases|7 cases|7例",
        "cases_8": r"eight cases|8 cases|8例",
        "deaths_3": r"three deaths|3 deaths|死亡3|3人.*死亡",
        "very_low": r"very low|非常に低い",
        "low": r"risk.*low|リスク.*低",
        "andes": r"Andes|ANDV|アンデス",
        "close_contacts": r"close contacts|濃厚接触|近接接触",
    }
    matches = {}
    for key, pattern in patterns.items():
        matches[key] = bool(re.search(pattern, clean, flags=re.I))
    result["matched"] = matches
    result["excerpt"] = clean[:1200]
    return result


def main() -> int:
    incident = json.loads(INCIDENT_PATH.read_text(encoding="utf-8"))
    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    now_utc = datetime.now(timezone.utc).isoformat()

    log = {
        "generated_at_utc": now_utc,
        "policy": "official-first; extracted signals are for human review",
        "sources": [],
    }

    for src in sources:
        status, body = fetch_url(src["url"])
        entry = {
            "id": src["id"],
            "name": src["name"],
            "url": src["url"],
            "status": status,
            "fetched_at_utc": now_utc,
        }
        if status and body:
            entry.update(extract_signals(src["id"], body))
        else:
            entry["error"] = body
        log["sources"].append(entry)

    # Refresh metadata only. Reviewed values remain in data/incident.json.
    incident.setdefault("meta", {})["fetchCheckedAtUtc"] = now_utc
    incident.setdefault("meta", {})["fetchPolicy"] = "official-first; KPI values are reviewed, not blindly scraped"

    INCIDENT_PATH.write_text(json.dumps(incident, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    FETCH_LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {INCIDENT_PATH.relative_to(ROOT)} and wrote {FETCH_LOG_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
