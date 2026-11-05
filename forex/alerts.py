"""Backend-only Forex alert events with in-process cooldown."""
from datetime import datetime,timezone,timedelta
import hashlib
from threading import RLock

class AlertEngine:
    def __init__(self,cooldown_seconds=300):
        self.cooldown=cooldown_seconds;self.sent={};self.lock=RLock()
    def reset(self):
        with self.lock: self.sent.clear()
    def evaluate(self,analysis,quote=None,now=None):
        now=now or datetime.now(timezone.utc)
        symbol=analysis['symbol'];tf=analysis['timeframe'];candidate=[]
        if analysis.get('data_status')!='OK':
            reason='; '.join(analysis.get('reasons',[])) or 'market data unavailable or stale'
            typ='MT5_DISCONNECTED' if 'disconnect' in reason.lower() else 'STALE_DATA' if analysis.get('data_status')=='STALE' else 'DATA_QUALITY'
            candidate.append((typ,'HIGH',reason))
        if (analysis.get('session') or {}).get('broker',{}).get('status') in ('CLOSED','DISABLED','UNKNOWN'):
            candidate.append(('BROKER_SESSION','MEDIUM','broker trading session unavailable'))
        if analysis.get('signal') in ('BUY','SELL') and analysis.get('plan'):
            candidate.append(('SETUP_CONFIRMED','MEDIUM',analysis['signal']+' setup confirmed'))
        if quote and quote.get('spread') is not None and quote.get('max_spread') is not None and quote['spread']>quote['max_spread']:
            candidate.append(('HIGH_SPREAD','HIGH','spread exceeds configured limit'))
        out=[]
        with self.lock:
            for typ,severity,reason in candidate:
                key=(symbol,tf,typ)
                old=self.sent.get(key)
                if old and (now-old).total_seconds()<self.cooldown: continue
                self.sent[key]=now
                event_id=hashlib.sha256(f'{symbol}|{tf}|{typ}|{now.isoformat()}'.encode()).hexdigest()[:20]
                out.append({'id':event_id,'expires_at':(now+timedelta(seconds=self.cooldown)).isoformat(),
                            'acknowledged':False,'type':typ,'severity':severity,'symbol':symbol,'timeframe':tf,
                            'timestamp':now.isoformat(),'source':'forex-backend','reason':reason})
        return out
