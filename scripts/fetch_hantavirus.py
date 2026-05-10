#!/usr/bin/env python3
import os,json,re,time,html,hashlib,requests,xml.etree.ElementTree as ET
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import quote_plus
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; JST=timezone(timedelta(hours=9)); UA='hantavirus-dashboard/0.6'
TERMS=['hantavirus','andv','andes virus','andes hantavirus','orthohantavirus','mv hondius','hondius']
def now(): return datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')
def sid(*p): return hashlib.sha1('|'.join(map(str,p)).encode()).hexdigest()[:16]
def get(url,**kw):
    h=kw.pop('headers',{}); h.setdefault('User-Agent',UA); return requests.get(url,headers=h,timeout=25,**kw)
def load(p,d):
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return d
def save(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def clean(s): return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',html.unescape(s or ''))).strip()
def is_h(it):
    hay=f"{it.get('title','')} {it.get('snippet','')} {it.get('abstract','')} {it.get('source','')}".lower(); return any(t in hay for t in TERMS)
def rss(url,kind='media',source=None,tier=2,limit=20):
    out=[]
    try:
        r=get(url); r.raise_for_status(); root=ET.fromstring(r.content); cand=root.findall('.//item') or root.findall('{http://www.w3.org/2005/Atom}entry')
        for item in cand[:limit*5]:
            title=item.findtext('title') or item.findtext('{http://www.w3.org/2005/Atom}title') or ''
            link=item.findtext('link') or ''
            le=item.find('{http://www.w3.org/2005/Atom}link')
            if not link and le is not None: link=le.attrib.get('href','')
            desc=clean(item.findtext('description') or item.findtext('summary') or item.findtext('{http://www.w3.org/2005/Atom}summary') or '')
            pub=item.findtext('pubDate') or item.findtext('{http://www.w3.org/2005/Atom}published') or ''
            it={'id':sid(source or url,title,link),'kind':kind,'tier':tier,'confidence':'low' if kind=='social' else ('expert-news' if kind=='academic' else 'reported'),'source':source or url,'title':title[:240],'url':link,'snippet':desc[:800],'published':pub}
            if is_h(it): out.append(it)
            if len(out)>=limit: break
    except Exception as e: out.append({'id':sid(url,'error'),'kind':kind,'tier':tier,'confidence':'fetch-error','source':source or url,'title':f'Fetch failed: {e}','url':url,'snippet':'','published':now()})
    return out
def gnews(q,kind='media',source=None,limit=20): return rss(f'https://news.google.com/rss/search?q={quote_plus(q)}&hl=en-US&gl=US&ceid=US:en',kind,source or f'Google News: {q}',2 if kind=='media' else 3,limit)
def bsky(q):
    try:
        r=get('https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts',params={'q':q,'limit':25,'sort':'latest'}); r.raise_for_status(); out=[]
        for p in r.json().get('posts',[]):
            rec=p.get('record',{}); au=p.get('author',{}); uri=p.get('uri',''); h=au.get('handle','unknown'); rk=uri.split('/')[-1] if uri else ''
            it={'id':sid('bsky',uri),'kind':'social','tier':1,'confidence':'low','source':'Bluesky','title':'@'+h,'url':f'https://bsky.app/profile/{h}/post/{rk}' if rk else 'https://bsky.app/','snippet':rec.get('text','')[:800],'published':rec.get('createdAt','')}
            if is_h(it): out.append(it)
        return out
    except Exception as e: return [{'id':sid('bsky','error'),'kind':'social','tier':1,'confidence':'fetch-error','source':'Bluesky','title':f'Fetch failed: {e}','url':'https://bsky.app/search?q=MV%20Hondius%20hantavirus','snippet':'','published':now()}]
def xsearch(q):
    tok=os.getenv('X_BEARER_TOKEN')
    if not tok: return [{'id':sid('x','no'),'kind':'social','tier':1,'confidence':'not-configured','source':'X/Twitter','title':'X_BEARER_TOKEN not configured','url':'https://developer.x.com/','snippet':'X recent search requires X_BEARER_TOKEN.','published':now()}]
    return []
def merge(new,old):
    seen=set(); out=[]
    for it in new+old:
        k=it.get('id') or it.get('url','')+'|'+it.get('title','')
        if k not in seen: seen.add(k); out.append(it)
    return out
def main():
    inc=load(DATA/'incident.json',{}); src=load(DATA/'sources.json',{}); old=load(DATA/'fetch_log.json',{'latest_items':[],'academic_items':[]})
    inc.setdefault('meta',{})['last_updated_jst']=now(); inc['meta']['data_last_checked_jst']=now(); inc['meta']['who_latest_url']='https://www.who.int/emergencies/disease-outbreak-news/item/2026-DON600'
    # WHO DON600 KPI values
    inc['kpis']=[{'label':'総症例','value':8,'source':'WHO DON 2026-05-08','class':'blue'},{'label':'確定例','value':6,'source':'WHO DON 2026-05-08','class':'teal'},{'label':'死亡','value':3,'source':'WHO DON 2026-05-08','class':'red'},{'label':'CFR','value':'38%','source':'WHO DON 2026-05-08','class':'orange'},{'label':'入院中','value':4,'source':'WHO DON 2026-05-08','class':'purple'},{'label':'船内対象者','value':147,'source':'WHO DON 2026-05-08','class':'green'}]
    media=[]
    for q in src.get('media_queries',[])[:12]: media+=gnews(q,'media',f'Google News: {q}',20); time.sleep(.2)
    for s in src.get('social_sources',[]):
        if s.get('kind')=='bsky': media+=bsky(s.get('query','MV Hondius hantavirus'))
        elif s.get('kind')=='rss': media+=rss(s['url'],'social',s.get('name'),1,20)
        elif s.get('kind')=='x_optional': media+=xsearch(s.get('query','MV Hondius hantavirus'))
    if not any(i.get('kind')=='social' for i in media): media.append({'id':sid('social',now()),'kind':'social','tier':1,'confidence':'status','source':'SNS fetch status','title':'No hantavirus-related SNS items fetched','url':'https://bsky.app/search?q=MV%20Hondius%20hantavirus','snippet':'SNS is low-confidence and filtered for hantavirus terms.','published':now()})
    acad=[]
    for feed in src.get('academic',{}).get('rss_feeds',[]): acad+=rss(feed['url'],'academic',feed['name'],3,20)
    for s in src.get('academic',{}).get('science_news_sources',[]): acad+=gnews(s.get('query','hantavirus'), 'academic', s.get('name','Science/expert news'),20)
    log={'generated_at':datetime.now(timezone.utc).isoformat(),'generated_at_jst':now(),'status':'ok','latest_items':merge([i for i in media if is_h(i) or i.get('confidence')=='status'],[i for i in old.get('latest_items',[]) if is_h(i) or i.get('confidence')=='status'])[:120],'academic_items':merge([i for i in acad if is_h(i)],[i for i in old.get('academic_items',[]) if is_h(i)])[:120],'notes':['WHO DON is used for top KPIs. Feeds are filtered to hantavirus-related items only.']}
    save(DATA/'incident.json',inc); save(DATA/'fetch_log.json',log)
if __name__=='__main__': main()
