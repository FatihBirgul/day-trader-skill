"""Explicit RSS and calendar ingestion with source and UTC provenance."""
from datetime import datetime,timezone
import re
from .core import DataError, legacy

news_skill=legacy('trader-news','news.py')
TOPICS={'CPI':r'\bcpi\b|consumer price','NFP':r'\bnfp\b|nonfarm payroll',
        'FOMC':r'\bfomc\b|federal reserve','ECB':r'\becb\b|european central bank',
        'BOE':r'\bboe\b|bank of england','GOLD':r'\bgold\b|\bxau\b'}
CURRENCIES={'USD':r'\busd\b|\bu\.s\.\b|federal reserve|\bfomc\b|\bnfp\b',
            'EUR':r'\beur\b|\becb\b|european central bank',
            'GBP':r'\bgbp\b|\bboe\b|bank of england',
            'JPY':r'\bjpy\b|bank of japan'}

def parse_rss(payload,source,now=None):
    if not source or not isinstance(source,str): raise DataError('source required')
    now=now or datetime.now(timezone.utc)
    try: raw=news_skill.parse_rss(payload,source)
    except Exception as exc: raise DataError('invalid RSS feed') from exc
    items=[]
    for item in raw:
        when=item.get('time')
        if when is None: continue
        if when.tzinfo is None: when=when.replace(tzinfo=timezone.utc)
        when=when.astimezone(timezone.utc)
        if when>now: continue
        title=item.get('title') or ''
        text=title+' '+(item.get('summary') or '')
        topics=[k for k,pattern in TOPICS.items() if re.search(pattern,text,re.I)]
        currencies=[k for k,pattern in CURRENCIES.items() if re.search(pattern,text,re.I)]
        if 'GOLD' in topics and 'USD' not in currencies: currencies.append('USD')
        if not currencies and not topics: continue
        item.update(source=source,time=when,touches=[],currencies=currencies,topics=topics)
        items.append(item)
    return [{'id':x['id'],'title':x['title'],'url':x['link'],'published_at':x['time'].isoformat(),
             'source':source,'currencies':x['currencies'],'topics':x['topics']} for x in news_skill.dedupe(items)]

def filter_events(events,symbol=None,start=None,end=None):
    out=[]
    related={'XAUUSD':{'USD'},'EURUSD':{'EUR','USD'},'GBPUSD':{'GBP','USD'},'USDJPY':{'USD','JPY'}}
    if symbol is not None and symbol not in related: raise DataError('unsupported symbol')
    for e in events:
        try:
            when=datetime.fromisoformat(e['time'].replace('Z','+00:00'))
            if when.tzinfo is None: raise ValueError('timezone missing')
            currency=e['currency'].upper()
            if not e.get('source') or not e.get('name') or not e.get('id') or currency not in ('USD','EUR','GBP','JPY'):
                raise ValueError('required event field missing')
            if symbol and currency not in related[symbol]: continue
            utc=when.astimezone(timezone.utc)
            if start and utc<start: continue
            if end and utc>end: continue
            out.append({**e,'currency':currency,'time':utc.isoformat()})
        except (KeyError,ValueError,TypeError) as exc: raise DataError('invalid calendar event') from exc
    return sorted(out,key=lambda e:(e['time'],e['id']))
