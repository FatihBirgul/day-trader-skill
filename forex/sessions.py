"""Informational global sessions and explicit broker-hours policy."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SESSIONS = {'Asian': ('Asia/Tokyo', 9, 18),
            'London': ('Europe/London', 8, 17),
            'New_York': ('America/New_York', 8, 17)}

def active_sessions(now):
    if now.tzinfo is None: raise ValueError('UTC-aware datetime required')
    names=[]
    for name,(zone,start,end) in SESSIONS.items():
        local=now.astimezone(ZoneInfo(zone))
        if local.weekday()<5 and start <= local.hour < end: names.append(name)
    if 'London' in names and 'New_York' in names: names.append('London_New_York_overlap')
    return names

def _minutes(value, allow_end=False):
    if not isinstance(value,str) or len(value)!=5 or value[2]!=':':
        raise ValueError('invalid HH:MM')
    h,m=int(value[:2]),int(value[3:])
    if h<0 or m<0 or m>59 or h>23 and not (allow_end and h==24 and m==0):
        raise ValueError('invalid HH:MM')
    return h*60+m

def broker_status(now, symbol, trade_allowed=None, hours=None, warning_minutes=30):
    """Explicit local broker schedule with overnight windows and date overrides."""
    if now.tzinfo is None: raise ValueError('UTC-aware datetime required')
    if trade_allowed is False: return {'status':'DISABLED','reason':'broker trading disabled'}
    if not hours:
        if now.weekday() in (5,6): return {'status':'CLOSED','reason':'Forex weekend; broker hours unverified'}
        return {'status':'UNKNOWN','reason':'broker hours not verified'}
    try:
        local=now.astimezone(ZoneInfo(hours['timezone']))
        weekly=hours['weekly']
        overrides=hours.get('date_overrides',{})
        if not isinstance(weekly,dict) or not isinstance(overrides,dict): raise ValueError('invalid policy')
        def windows(day):
            date=day.date().isoformat()
            if date in overrides:
                value=overrides[date]
                if value is None: return []
                return value
            return weekly.get(str(day.weekday()),[])
        minute=local.hour*60+local.minute
        for day,offset in ((local,-0),(local-timedelta(days=1),1440)):
            for pair in windows(day):
                start,end=pair
                a,b=_minutes(start),_minutes(end,True)
                if a==b: raise ValueError('zero-length window')
                if b<a: b+=1440
                current=minute+offset
                if a<=current<b:
                    remaining=b-current
                    return {'status':'CLOSING_SOON' if remaining<=warning_minutes else 'OPEN',
                            'reason':'configured broker hours','closes_at':end}
                if offset==0 and 0<a-current<=warning_minutes:
                    return {'status':'OPENING_SOON','reason':'configured broker hours','opens_at':start}
        return {'status':'CLOSED','reason':'outside configured broker hours'}
    except (KeyError,TypeError,ValueError,IndexError) as exc:
        return {'status':'UNKNOWN','reason':f'invalid broker-hours policy: {exc}'}

def session_snapshot(now, symbol, trade_allowed=None, hours=None):
    return {'timestamp':now.astimezone(timezone.utc).isoformat(), 'symbol':symbol,
            'sessions':active_sessions(now),'broker':broker_status(now,symbol,trade_allowed,hours)}
