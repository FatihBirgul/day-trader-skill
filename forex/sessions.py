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

def broker_status(now, symbol, trade_allowed=None, hours=None, warning_minutes=30):
    """Policy is explicit {timezone, weekly:{weekday:[[HH:MM, HH:MM],...]}}.

    An absent policy is UNKNOWN on weekdays, never inferred OPEN from sessions.
    """
    if now.tzinfo is None: raise ValueError('UTC-aware datetime required')
    if trade_allowed is False: return {'status':'CLOSED','reason':'broker trading disabled'}
    if now.weekday() == 5 or (now.weekday() == 6 and now.hour < 21):
        return {'status':'CLOSED','reason':'Forex weekend'}
    if not hours: return {'status':'UNKNOWN','reason':'broker hours not verified'}
    try:
        local=now.astimezone(ZoneInfo(hours['timezone']))
        day=str(local.weekday()); current=local.hour*60+local.minute
        windows=hours['weekly'].get(day,[])
        for start,end in windows:
            sh,sm=map(int,start.split(':'));eh,em=map(int,end.split(':'))
            a,b=sh*60+sm,eh*60+em
            if not 0<=a<1440 or not 0<=b<=1440 or a>=b: raise ValueError('invalid hours')
            if a<=current<b:
                return {'status':'CLOSING_SOON' if b-current<=warning_minutes else 'OPEN',
                        'reason':'configured broker hours','closes_at':end}
            if 0<a-current<=warning_minutes:
                return {'status':'OPENING_SOON','reason':'configured broker hours','opens_at':start}
        return {'status':'CLOSED','reason':'outside configured broker hours'}
    except (KeyError,TypeError,ValueError) as exc:
        return {'status':'UNKNOWN','reason':f'invalid broker-hours policy: {exc}'}

def session_snapshot(now, symbol, trade_allowed=None, hours=None):
    return {'timestamp':now.astimezone(timezone.utc).isoformat(), 'symbol':symbol,
            'sessions':active_sessions(now),'broker':broker_status(now,symbol,trade_allowed,hours)}
