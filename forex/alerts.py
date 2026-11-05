"""Backend-only Forex alert events with in-process cooldown."""
from datetime import datetime,timezone
from threading import RLock

class AlertEngine:
    def __init__(self,cooldown_seconds=300):
        self.cooldown=cooldown_seconds;self.sent={};self.lock=RLock()
    def evaluate(self,analysis,quote=None,now=None):
        now=now or datetime.now(timezone.utc)
        symbol=analysis['symbol'];tf=analysis['timeframe'];candidate=[]
        if analysis.get('data_status')!='OK':
            candidate.append(('DATA_QUALITY','HIGH','market data unavailable or stale'))
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
                out.append({'type':typ,'severity':severity,'symbol':symbol,'timeframe':tf,
                            'timestamp':now.isoformat(),'source':'forex-backend','reason':reason})
        return out
