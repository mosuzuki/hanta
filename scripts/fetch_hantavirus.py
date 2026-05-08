#!/usr/bin/env python3
import os, json, re, time, html, hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote_plus, urlencode
import requests
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
JST = timezone(timedelta(hours=9))
UA = "hantavirus-risk-dashboard/0.3 (+https://github.com/)"

def now_jst():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

def get(url, timeout=25, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", UA)
    return requests.get(url, headers=headers, timeout=timeout, **kwargs)

def load_json(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default

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
        for item in root.findall(".//item")[:limit*3]:
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            desc = strip_html(item.findtext("description") or "")
            pub = item.findtext("pubDate") or item.findtext("{http://purl.org/dc/elements/1.1/}date") or ""
            hay = f"{title} {desc}".lower()
            if keyword_filter and not any(k.lower() in hay for k in keyword_filter):
                continue
            items.append({
                "id": stable_id(source_name or url, title, link),
                "kind": kind,
                "tier": tier,
                "confidence": "low" if kind == "social" else "reported",
                "source": source_name or url,
                "title": title[:240],
                "url": link,
                "snippet": desc[:700],
                "published": pub
            })
            if len(items) >= limit: break
    except Exception as e:
        items.append({"id": stable_id(url, "error"), "kind": kind, "tier": tier, "confidence": "fetch-error", "source": source_name or url, "title": f"Fetch failed: {e}", "url": url, "snippet": "", "published": now_jst()})
    return items

def fetch_bluesky(query, limit=10):
    items = []
    try:
        url = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
        r = get(url, params={"q": query, "limit": min(limit, 25), "sort": "latest"})
        r.raise_for_status()
        for post in r.json().get("posts", [])[:limit]:
            record, author = post.get("record", {}), post.get("author", {})
            uri = post.get("uri", "")
            handle = author.get("handle", "unknown")
            rkey = uri.split("/")[-1] if uri else ""
            link = f"https://bsky.app/profile/{handle}/post/{rkey}" if handle and rkey else "https://bsky.app/"
            text = record.get("text", "")
            items.append({"id": stable_id("bsky", uri, text), "kind":"social", "tier":1, "confidence":"low", "source":"Bluesky", "title":f"@{handle}", "url":link, "snippet":text[:700], "published":record.get("createdAt","")})
    except Exception as e:
        items.append({"id": stable_id("bsky","error"), "kind":"social", "tier":1, "confidence":"fetch-error", "source":"Bluesky", "title":f"Fetch failed: {e}", "url":"https://bsky.app/search", "snippet":"", "published":now_jst()})
    return items

def fetch_x_optional(query, limit=10):
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
        return [{"id": stable_id("x","error"), "kind":"social", "tier":1, "confidence":"fetch-error", "source":"X/Twitter", "title":f"Fetch failed: {e}", "url":"https://x.com/search", "snippet":"", "published":now_jst()}]

def fetch_media_google_news(query, limit=10):
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    return parse_rss(url, kind="media", source_name=f"Google News: {query}", tier=2, limit=limit)

def pubmed_search(query, days_back=365, retmax=25):
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    mindate = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y/%m/%d")
    params = {
        "db":"pubmed", "term": query, "retmode":"json", "retmax":str(retmax),
        "sort":"pub date", "datetype":"pdat", "mindate":mindate
    }
    r = get(base, params=params)
    r.raise_for_status()
    return r.json().get("esearchresult", {}).get("idlist", [])

def pubmed_fetch(pmids):
    if not pmids: return []
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    r = get(url, params={"db":"pubmed", "id":",".join(pmids), "retmode":"xml"})
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
        pub = " ".join([year, month]).strip()
        out.append({"pmid":pmid, "title":title, "journal":journal, "year":year, "published":pub, "abstract":abstract[:1800], "doi":doi, "url":f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", "source":"PubMed"})
    return out

def openai_translate_academic(items, model):
    key = os.getenv("OPENAI_API_KEY")
    if not key or not items:
        for it in items:
            it["title_ja"] = it.get("title","")
            if it.get("abstract"):
                it["summary_ja"] = "日本語要約は未生成です。OPENAI_API_KEYを設定すると、タイトル和訳と日本語要約を自動生成します。英文要旨: " + it["abstract"][:280]
            else:
                it["summary_ja"] = "要旨なし。OPENAI_API_KEYを設定すると、利用可能な本文情報から日本語要約を生成します。"
        return items

    try:
        payload_items = [{"id":it.get("pmid") or it.get("id"), "title":it.get("title",""), "abstract":it.get("abstract",""), "journal":it.get("journal","")} for it in items[:20]]
        prompt = (
            "以下のハンタウイルス関連文献について、日本語タイトルと2文以内の日本語要約を作成してください。"
            "医学・公衆衛生の専門家向けに、過度な断定を避け、原文にない情報は追加しないでください。"
            "JSON配列で返してください。各要素は id, title_ja, summary_ja のみ。\n\n"
            + json.dumps(payload_items, ensure_ascii=False)
        )
        r = requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization":f"Bearer {key}", "Content-Type":"application/json", "User-Agent":UA},
            json={"model":model, "messages":[{"role":"user","content":prompt}], "temperature":0.2},
            timeout=60)
        r.raise_for_status()
        txt = r.json()["choices"][0]["message"]["content"]
        # tolerate fenced json
        txt = re.sub(r"^```json\s*|\s*```$", "", txt.strip(), flags=re.S)
        trans = {str(x["id"]): x for x in json.loads(txt)}
        for it in items:
            tid = str(it.get("pmid") or it.get("id"))
            if tid in trans:
                it["title_ja"] = trans[tid].get("title_ja", it.get("title",""))
                it["summary_ja"] = trans[tid].get("summary_ja", "")
            else:
                it["title_ja"] = it.get("title","")
                it["summary_ja"] = "要約未生成。"
    except Exception as e:
        for it in items:
            it["title_ja"] = it.get("title","")
            it["summary_ja"] = f"OpenAIによる和訳・要約生成に失敗: {e}. 英文要旨: {it.get('abstract','')[:260]}"
    return items

def fetch_academic(sources):
    cfg = sources.get("academic", {})
    pmids = pubmed_search(cfg.get("pubmed_query","hantavirus"), cfg.get("days_back",365), cfg.get("pubmed_retmax",25))
    items = pubmed_fetch(pmids)
    priority = [j.lower() for j in cfg.get("priority_journals", [])]
    for it in items:
        it["kind"] = "academic"
        it["id"] = stable_id("pubmed", it.get("pmid"))
        j = it.get("journal","").lower()
        it["priority"] = any(p in j for p in priority)
    # RSS feeds from major journals, filtered by hantavirus terms
    keywords = ["hantavirus", "orthohantavirus", "andes virus", "hantaan", "seoul virus", "puumala"]
    for feed in cfg.get("rss_feeds", []):
        for rss in parse_rss(feed["url"], kind="academic", source_name=feed["name"], tier=3, limit=10, keyword_filter=keywords):
            items.append({
                "id": rss["id"], "kind":"academic", "title":rss["title"], "title_ja":rss["title"], "journal":feed["name"],
                "published":rss["published"], "year":"", "abstract":rss["snippet"], "summary_ja":"日本語要約は未生成です。OPENAI_API_KEYを設定すると自動生成します。",
                "url":rss["url"], "source":"journal RSS", "doi":"", "priority": True
            })
    # de-duplicate and sort with rough priority
    seen, clean = set(), []
    for it in items:
        key = (it.get("pmid") or "") + "|" + (it.get("doi") or "") + "|" + it.get("title","").lower()
        if key in seen or not it.get("title"): continue
        seen.add(key); clean.append(it)
    clean = openai_translate_academic(clean[:30], cfg.get("openai_model","gpt-4.1-mini"))
    return clean

def fetch_cruisemapper_position():
    url = "https://www.cruisemapper.com/ships/MV-Hondius-1624"
    try:
        r = get(url)
        r.raise_for_status()
        text = strip_html(r.text)
        # This is intentionally conservative; coordinates are not parsed unless explicit.
        m = re.search(r"current location of MV Hondius is ([^.]{10,180})\.", text, re.I)
        if m:
            return {"label":m.group(1), "source":url, "timestamp":now_jst(), "confidence":"external-unverified"}
        return {"source":url, "timestamp":now_jst(), "confidence":"not-parsed"}
    except Exception as e:
        return {"error":str(e), "source":url, "timestamp":now_jst()}

def main():
    incident = load_json(DATA/"incident.json", {})
    sources = load_json(DATA/"sources.json", {})
    items = []

    for q in sources.get("media_queries", [])[:8]:
        items.extend(fetch_media_google_news(q, limit=7))
        time.sleep(0.25)

    for s in sources.get("social_sources", []):
        if s.get("kind") == "bsky":
            items.extend(fetch_bluesky(s.get("query","MV Hondius hantavirus"), limit=12))
        elif s.get("kind") == "rss":
            items.extend(parse_rss(s["url"], kind="social", source_name=s.get("name"), tier=s.get("tier",1), limit=12))
        elif s.get("kind") == "x_optional":
            items.extend(fetch_x_optional(s.get("query",'"MV Hondius" OR "hantavirus cruise ship"'), limit=12))
        time.sleep(0.25)

    seen, clean = set(), []
    for it in items:
        key = it.get("id") or ((it.get("url") or "") + "|" + (it.get("title") or ""))
        if key in seen: continue
        seen.add(key); clean.append(it)

    academic_items = []
    try:
        academic_items = fetch_academic(sources)
    except Exception as e:
        academic_items = [{"kind":"academic", "source":"fetch-error", "title":f"Academic fetch failed: {e}", "title_ja":"学術文献取得に失敗", "summary_ja":str(e), "url":"", "published":now_jst(), "journal":"", "priority":False}]

    incident.setdefault("meta", {})["last_updated_jst"] = now_jst()
    pos = fetch_cruisemapper_position()
    if "label" in pos and incident.get("route", {}).get("position"):
        # Update text only; coordinates are kept from curated seed unless a proper API is added.
        incident["route"]["position"]["label"] = pos["label"]
        incident["route"]["position"]["timestamp"] = pos["timestamp"]
        incident["route"]["position"]["source"] = pos["source"]
        incident["route"]["position"]["confidence"] = pos["confidence"]

    log = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_at_jst": now_jst(),
        "status": "ok",
        "ship_position_fetch": pos,
        "latest_items": clean[:90],
        "academic_items": academic_items[:30],
        "notes": [
            "Official KPIs are not overwritten by media, SNS, or academic feeds.",
            "SNS items are low-confidence signals for situational awareness only.",
            "Academic title translation/summaries require OPENAI_API_KEY; otherwise fallback text is shown.",
            "For precise ship position, use a licensed AIS provider API and update data/incident.json route.position."
        ]
    }
    save_json(DATA/"incident.json", incident)
    save_json(DATA/"fetch_log.json", log)

if __name__ == "__main__":
    main()
