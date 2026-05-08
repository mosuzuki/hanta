#!/usr/bin/env python3
"""
Fetch public information for the MV Hondius hantavirus incident dashboard.

Design:
- Official sources never get overwritten by SNS or media signals.
- Media/social signals are stored in data/fetch_log.json as low-confidence signals.
- X/Twitter is optional and requires X_BEARER_TOKEN.
- Bluesky, Mastodon RSS and Reddit RSS are best-effort public sources.
- Ship position is best-effort. If AIS-like pages cannot be parsed reliably, the script
  preserves the existing manual/seed position and appends a note.
"""
import os, json, re, time, email.utils
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote_plus
import requests
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
JST = timezone(timedelta(hours=9))
UA = "hantavirus-risk-dashboard/0.2 (+https://github.com/)"

def now_jst():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

def get(url, timeout=20):
    return requests.get(url, headers={"User-Agent": UA}, timeout=timeout)

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def save_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()

def parse_rss(url, kind="social", source_name=None, tier=1, limit=10):
    items = []
    try:
        r = get(url)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            desc = strip_html(item.findtext("description") or "")
            pub = item.findtext("pubDate") or ""
            items.append({
                "kind": kind,
                "tier": tier,
                "confidence": "low" if kind == "social" else "reported",
                "source": source_name or url,
                "title": title[:220],
                "url": link,
                "snippet": desc[:500],
                "published": pub
            })
    except Exception as e:
        items.append({"kind": kind, "tier": tier, "confidence": "fetch-error", "source": source_name or url, "title": f"Fetch failed: {e}", "url": url, "snippet": "", "published": now_jst()})
    return items

def fetch_bluesky(query, limit=10):
    # Public XRPC endpoint. It can rate-limit or fail; failures are logged but non-fatal.
    items = []
    url = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
    params = {"q": query, "limit": min(limit, 25), "sort": "latest"}
    try:
        r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=20)
        r.raise_for_status()
        for post in r.json().get("posts", [])[:limit]:
            record = post.get("record", {})
            author = post.get("author", {})
            uri = post.get("uri", "")
            handle = author.get("handle", "unknown")
            # bsky app link can be derived from handle and rkey
            rkey = uri.split("/")[-1] if uri else ""
            link = f"https://bsky.app/profile/{handle}/post/{rkey}" if handle and rkey else "https://bsky.app/"
            text = record.get("text", "")
            created = record.get("createdAt", "")
            items.append({
                "kind": "social",
                "tier": 1,
                "confidence": "low",
                "source": "Bluesky",
                "title": f"@{handle}",
                "url": link,
                "snippet": text[:500],
                "published": created
            })
    except Exception as e:
        items.append({"kind": "social", "tier": 1, "confidence": "fetch-error", "source": "Bluesky", "title": f"Fetch failed: {e}", "url": url, "snippet": "", "published": now_jst()})
    return items

def fetch_x_optional(query, limit=10):
    token = os.getenv("X_BEARER_TOKEN")
    if not token:
        return [{"kind": "social", "tier": 1, "confidence": "not-configured", "source": "X/Twitter", "title": "X_BEARER_TOKEN not configured", "url": "https://developer.x.com/", "snippet": "Set a repository secret named X_BEARER_TOKEN to enable X recent search.", "published": now_jst()}]
    try:
        url = "https://api.twitter.com/2/tweets/search/recent"
        params = {"query": query, "max_results": min(max(limit, 10), 100), "tweet.fields": "created_at,author_id"}
        r = requests.get(url, params=params, headers={"Authorization": f"Bearer {token}", "User-Agent": UA}, timeout=20)
        r.raise_for_status()
        out = []
        for tw in r.json().get("data", [])[:limit]:
            out.append({
                "kind": "social", "tier": 1, "confidence": "low", "source": "X/Twitter",
                "title": f"Tweet {tw.get('id')}", "url": f"https://x.com/i/web/status/{tw.get('id')}",
                "snippet": tw.get("text","")[:500], "published": tw.get("created_at","")
            })
        return out
    except Exception as e:
        return [{"kind": "social", "tier": 1, "confidence": "fetch-error", "source": "X/Twitter", "title": f"Fetch failed: {e}", "url": "https://x.com/search", "snippet": "", "published": now_jst()}]

def fetch_media_google_news(query, limit=10):
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    return parse_rss(url, kind="media", source_name=f"Google News: {query}", tier=2, limit=limit)

def fetch_cruisemapper_position():
    # Best effort: current position pages are not stable and may block scraping.
    url = "https://www.cruisemapper.com/ships/MV-Hondius-1624"
    try:
        r = get(url, timeout=20)
        r.raise_for_status()
        text = strip_html(r.text)
        m = re.search(r"current location of MV Hondius is ([^.]{10,180})\.", text, re.I)
        if m:
            return {"label": m.group(1), "source": url, "timestamp": now_jst(), "confidence": "external-unverified"}
    except Exception as e:
        return {"error": str(e), "source": url, "timestamp": now_jst()}
    return {"source": url, "timestamp": now_jst(), "confidence": "not-parsed"}

def main():
    incident = load_json(DATA / "incident.json", {})
    sources = load_json(DATA / "sources.json", {})
    items = []

    for q in sources.get("media_queries", [])[:6]:
        items.extend(fetch_media_google_news(q, limit=6))
        time.sleep(0.5)

    for s in sources.get("social_sources", []):
        kind = s.get("kind")
        if kind == "bsky":
            items.extend(fetch_bluesky(s.get("query", "MV Hondius hantavirus"), limit=10))
        elif kind == "rss":
            items.extend(parse_rss(s["url"], kind="social", source_name=s.get("name"), tier=s.get("tier", 1), limit=10))
        elif kind == "x_optional":
            items.extend(fetch_x_optional(s.get("query", '"MV Hondius" OR "hantavirus cruise ship"'), limit=10))
        time.sleep(0.5)

    # Dedupe roughly by URL/title
    seen, clean = set(), []
    for it in items:
        key = (it.get("url") or "") + "|" + (it.get("title") or "")
        if key in seen:
            continue
        seen.add(key)
        clean.append(it)
    clean = clean[:80]

    # Update timestamp and try to update position text without changing manual coordinates.
    incident.setdefault("meta", {})["last_updated_jst"] = now_jst()
    pos = fetch_cruisemapper_position()
    if "label" in pos and incident.get("route", {}).get("position"):
        incident["route"]["position"]["label"] = pos["label"]
        incident["route"]["position"]["timestamp"] = pos["timestamp"]
        incident["route"]["position"]["source"] = pos["source"]
        incident["route"]["position"]["confidence"] = pos["confidence"]

    log = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_at_jst": now_jst(),
        "status": "ok",
        "ship_position_fetch": pos,
        "latest_items": clean,
        "notes": [
            "Official KPIs are not overwritten by media or SNS.",
            "SNS items are low-confidence signals for situational awareness only.",
            "Review data/incident.json manually when official WHO/ECDC values change."
        ]
    }
    save_json(DATA / "incident.json", incident)
    save_json(DATA / "fetch_log.json", log)

if __name__ == "__main__":
    main()
