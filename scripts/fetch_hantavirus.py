#!/usr/bin/env python3
import os, json, re, time, html, hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote_plus
import requests
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
JST = timezone(timedelta(hours=9))
UA = "hantavirus-risk-dashboard/0.5 (+https://github.com/)"

def now_jst():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()

def get(url, timeout=25, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", UA)
    return requests.get(url, headers=headers, timeout=timeout, **kwargs)

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def save_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def strip_html(s):
    s = html.unescape(s or "")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()

def stable_id(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:16]

def parse_rss(url, kind="social", source_name=None, tier=1, limit=10, keyword_filter=None):
    items = []
    try:
        r = get(url)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        candidates = root.findall(".//item") or root.findall("{http://www.w3.org/2005/Atom}entry")
        for item in candidates[:limit*4]:
            title = item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title") or ""
            link = item.findtext("link") or ""
            if not link:
                link_el = item.find("{http://www.w3.org/2005/Atom}link")
                if link_el is not None:
                    link = link_el.attrib.get("href", "")
            desc = strip_html(item.findtext("description") or item.findtext("summary") or item.findtext("{http://www.w3.org/2005/Atom}summary") or "")
            pub = item.findtext("pubDate") or item.findtext("published") or item.findtext("{http://www.w3.org/2005/Atom}published") or item.findtext("{http://purl.org/dc/elements/1.1/}date") or ""
            hay = f"{title} {desc}".lower()
            if keyword_filter and not any(k.lower() in hay for k in keyword_filter):
                continue
            items.append({
                "id": stable_id(source_name or url, title, link),
                "kind": kind,
                "tier": tier,
                "confidence": "low" if kind == "social" else ("reported" if kind == "media" else "expert-news"),
                "source": source_name or url,
                "title": title[:240],
                "url": link,
                "snippet": desc[:700],
                "published": pub
            })
            if len(items) >= limit:
                break
    except Exception as e:
        items.append({"id": stable_id(url, "error"), "kind": kind, "tier": tier, "confidence": "fetch-error", "source": source_name or url, "title": f"Fetch failed: {e}", "url": url, "snippet": "", "published": now_jst()})
    return items

def fetch_google_news(query, kind="media", source_name=None, limit=10):
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    return parse_rss(url, kind=kind, source_name=source_name or f"Google News: {query}", tier=2 if kind=="media" else 3, limit=limit)

def fetch_bluesky(query, limit=12):
    try:
        url = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
        r = get(url, params={"q": query, "limit": min(limit, 25), "sort": "latest"})
        r.raise_for_status()
        out = []
        for post in r.json().get("posts", [])[:limit]:
            record, author = post.get("record", {}), post.get("author", {})
            uri = post.get("uri", "")
            handle = author.get("handle", "unknown")
            rkey = uri.split("/")[-1] if uri else ""
            link = f"https://bsky.app/profile/{handle}/post/{rkey}" if handle and rkey else "https://bsky.app/"
            out.append({"id": stable_id("bsky", uri), "kind":"social", "tier":1, "confidence":"low", "source":"Bluesky", "title":f"@{handle}", "url":link, "snippet":record.get("text","")[:700], "published":record.get("createdAt","")})
        return out or [{"id": stable_id("bsky","empty",now_jst()), "kind":"social", "tier":1, "confidence":"empty", "source":"Bluesky", "title":"No matching Bluesky posts", "url":"https://bsky.app/search?q=MV%20Hondius%20hantavirus", "snippet":"No matching public posts returned in this run.", "published":now_jst()}]
    except Exception as e:
        return [{"id": stable_id("bsky","error"), "kind":"social", "tier":1, "confidence":"fetch-error", "source":"Bluesky", "title":f"Fetch failed: {e}", "url":"https://bsky.app/search?q=MV%20Hondius%20hantavirus", "snippet":"", "published":now_jst()}]

def fetch_x_optional(query, limit=12):
    token = os.getenv("X_BEARER_TOKEN")
    if not token:
        return [{"id": stable_id("x","not-configured"), "kind":"social", "tier":1, "confidence":"not-configured", "source":"X/Twitter", "title":"X_BEARER_TOKEN not configured", "url":"https://developer.x.com/", "snippet":"GitHub SecretsにX_BEARER_TOKENを設定するとX recent searchを取得します。", "published":now_jst()}]
    try:
        url = "https://api.twitter.com/2/tweets/search/recent"
        params = {"query": query, "max_results": min(max(limit,10),100), "tweet.fields":"created_at,author_id"}
        r = get(url, headers={"Authorization": f"Bearer {token}"}, params=params)
        r.raise_for_status()
        out = []
        for tw in r.json().get("data", [])[:limit]:
            out.append({"id": stable_id("x", tw.get("id")), "kind":"social", "tier":1, "confidence":"low", "source":"X/Twitter", "title":f"Tweet {tw.get('id')}", "url":f"https://x.com/i/web/status/{tw.get('id')}", "snippet":tw.get("text","")[:700], "published":tw.get("created_at","")})
        return out
    except Exception as e:
        return [{"id": stable_id("x","error"), "kind":"social", "tier":1, "confidence":"fetch-error", "source":"X/Twitter", "title":f"Fetch failed: {e}", "url":"https://x.com/search?q=MV%20Hondius%20hantavirus", "snippet":"", "published":now_jst()}]

def pubmed_search(query, days_back=365, retmax=25):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    mindate = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y/%m/%d")
    r = get(url, params={"db":"pubmed","term":query,"retmode":"json","retmax":retmax,"sort":"pub date","datetype":"pdat","mindate":mindate})
    r.raise_for_status()
    return r.json().get("esearchresult", {}).get("idlist", [])

def pubmed_fetch(pmids):
    if not pmids:
        return []
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    r = get(url, params={"db":"pubmed","id":",".join(pmids),"retmode":"xml"})
    r.raise_for_status()
    root = ET.fromstring(r.content)
    out = []
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//PMID") or ""
        title = strip_html("".join(art.findtext(".//ArticleTitle") or ""))
        journal = art.findtext(".//Journal/Title") or art.findtext(".//Journal/ISOAbbreviation") or ""
        year = art.findtext(".//JournalIssue/PubDate/Year") or art.findtext(".//ArticleDate/Year") or ""
        month = art.findtext(".//JournalIssue/PubDate/Month") or ""
        abstract = " ".join(strip_html("".join(x.itertext())) for x in art.findall(".//Abstract/AbstractText"))
        doi = ""
        for aid in art.findall(".//ArticleId"):
            if aid.attrib.get("IdType") == "doi":
                doi = aid.text or ""
        out.append({"pmid":pmid,"id":stable_id("pubmed",pmid),"kind":"academic","title":title,"title_ja":title,"journal":journal,"year":year,"published":" ".join([year,month]).strip(),"abstract":abstract[:1800],"summary_ja":"日本語要約は未生成です。OPENAI_API_KEYを設定すると自動生成します。","doi":doi,"url":f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/","source":"PubMed","source_type":"peer-reviewed","priority":False})
    return out

def fetch_academic(sources):
    cfg = sources.get("academic", {})
    items = []
    try:
        pmids = pubmed_search(cfg.get("pubmed_query", "hantavirus OR orthohantavirus"), cfg.get("days_back", 365), cfg.get("pubmed_retmax", 25))
        items.extend(pubmed_fetch(pmids))
    except Exception as e:
        items.append({"id":stable_id("pubmed-error",str(e)),"kind":"academic","source":"PubMed","source_type":"fetch-error","title":f"PubMed fetch failed: {e}","title_ja":"PubMed取得に失敗","journal":"PubMed","published":now_jst(),"year":"","abstract":"","summary_ja":str(e),"url":"","doi":"","priority":False})

    keywords = ["hantavirus","orthohantavirus","andes virus","hantaan","seoul virus","puumala","MV Hondius".lower()]
    for feed in cfg.get("rss_feeds", []):
        for rss in parse_rss(feed["url"], kind="academic", source_name=feed["name"], tier=3, limit=10, keyword_filter=keywords):
            items.append({"id":rss["id"],"kind":"academic","source":feed["name"],"source_type":"journal-rss","title":rss["title"],"title_ja":rss["title"],"journal":feed["name"],"published":rss["published"],"year":"","abstract":rss["snippet"],"summary_ja":"日本語要約は未生成です。OPENAI_API_KEYを設定すると自動生成します。","url":rss["url"],"doi":"","priority":True})

    for src in cfg.get("science_news_sources", []):
        for x in fetch_google_news(src.get("query","hantavirus cruise ship"), kind="academic", source_name=src.get("name","Science news"), limit=6):
            items.append({"id":x["id"],"kind":"academic","source":src.get("name","Science news"),"source_type":"science-news","title":x["title"],"title_ja":x["title"],"journal":src.get("name","Science news"),"published":x["published"],"year":"","abstract":x["snippet"],"summary_ja":"専門ニュース・解説記事です。OPENAI_API_KEYを設定すると日本語要約を自動生成します。 "+x["snippet"][:260],"url":x["url"],"doi":"","priority":True})

    # Deduplicate
    seen, clean = set(), []
    for it in items:
        key = (it.get("pmid") or "") + "|" + (it.get("doi") or "") + "|" + it.get("title","").lower() + "|" + it.get("url","")
        if key in seen or not it.get("title"):
            continue
        seen.add(key)
        clean.append(it)
    return clean[:40]

def fetch_cruisemapper_position():
    url = "https://www.cruisemapper.com/ships/MV-Hondius-1624"
    try:
        r = get(url)
        r.raise_for_status()
        text = strip_html(r.text)
        m = re.search(r"current location of MV Hondius is ([^.]{10,180})\.", text, re.I)
        if m:
            return {"label":m.group(1), "source":url, "timestamp":now_jst(), "confidence":"external-unverified"}
    except Exception as e:
        return {"error":str(e), "source":url, "timestamp":now_jst()}
    return {"source":url, "timestamp":now_jst(), "confidence":"not-parsed"}

def merge_unique(new, old):
    seen, out = set(), []
    for it in new + old:
        key = it.get("id") or (it.get("url","") + "|" + it.get("title",""))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out

def main():
    incident = load_json(DATA/"incident.json", {})
    sources = load_json(DATA/"sources.json", {})
    old_log = load_json(DATA/"fetch_log.json", {"latest_items":[],"academic_items":[]})
    errors = []

    incident.setdefault("meta", {})["last_updated_jst"] = now_jst()
    incident.setdefault("meta", {})["data_last_checked_jst"] = now_jst()

    media_social = []
    try:
        for q in sources.get("media_queries", [])[:10]:
            media_social.extend(fetch_google_news(q, kind="media", source_name=f"Google News: {q}", limit=8))
            time.sleep(0.2)
    except Exception as e:
        errors.append(f"media: {e}")

    try:
        for s in sources.get("social_sources", []):
            if s.get("kind") == "bsky":
                media_social.extend(fetch_bluesky(s.get("query","MV Hondius hantavirus"), limit=12))
            elif s.get("kind") == "rss":
                media_social.extend(parse_rss(s["url"], kind="social", source_name=s.get("name"), tier=s.get("tier",1), limit=12))
            elif s.get("kind") == "x_optional":
                media_social.extend(fetch_x_optional(s.get("query",'"MV Hondius" OR "hantavirus cruise ship"'), limit=12))
            time.sleep(0.2)
    except Exception as e:
        errors.append(f"social: {e}")

    if not any(x.get("kind") == "social" for x in media_social):
        media_social.append({"id":stable_id("social-empty",now_jst()),"kind":"social","tier":1,"confidence":"empty","source":"SNS fetch status","title":"No SNS items fetched","url":"https://bsky.app/search?q=MV%20Hondius%20hantavirus","snippet":"No public SNS items were fetched in this run. X requires X_BEARER_TOKEN.","published":now_jst()})

    try:
        academic = fetch_academic(sources)
    except Exception as e:
        errors.append(f"academic: {e}")
        academic = []

    pos = fetch_cruisemapper_position()
    if "label" in pos and incident.get("route", {}).get("position"):
        incident["route"]["position"]["label"] = pos["label"]
        incident["route"]["position"]["timestamp"] = pos["timestamp"]
        incident["route"]["position"]["source"] = pos["source"]
        incident["route"]["position"]["confidence"] = pos["confidence"]

    latest_items = merge_unique(media_social, old_log.get("latest_items", []))[:120]
    academic_items = merge_unique(academic, old_log.get("academic_items", []))[:60]

    log = {
        "generated_at": now_utc_iso(),
        "generated_at_jst": now_jst(),
        "status": "ok" if not errors else "partial",
        "errors": errors,
        "ship_position_fetch": pos,
        "latest_items": latest_items,
        "academic_items": academic_items,
        "notes": [
            "Official KPIs are not overwritten by media, SNS, or academic feeds.",
            "SNS items are low-confidence signals only.",
            "The dashboard timestamp updates every successful Actions run.",
            "If GitHub Pages does not show the new timestamp, wait for pages-build-deployment or clear cache."
        ]
    }

    save_json(DATA/"incident.json", incident)
    save_json(DATA/"fetch_log.json", log)

if __name__ == "__main__":
    main()
