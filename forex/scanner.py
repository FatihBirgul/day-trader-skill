"""Multi-symbol scanner composed from the existing Forex analysis pipeline."""
from datetime import datetime, timezone
from .core import SYMBOLS, TIMEFRAMES, analyze

def scan(provider, symbols=SYMBOLS, timeframes=('M15',), now=None, limit=24):
    pairs=[(s,t) for s in symbols for t in timeframes]
    if len(pairs)>limit: raise ValueError('scanner request exceeds pair limit')
    if any(s not in SYMBOLS or t not in TIMEFRAMES for s,t in pairs):
        raise ValueError('unsupported symbol or timeframe')
    when=now or datetime.now(timezone.utc).timestamp()
    results=[];errors=[]
    for symbol,tf in pairs:
        try:
            result=analyze(provider,symbol,tf,now=when)
            results.append({'symbol':symbol,'timeframe':tf,'signal':result['signal'],
                            'data_status':result['data_status'],'reasons':result['reasons'],
                            'session':result.get('session'),'indicators':result.get('indicators'),
                            'strategies':result.get('strategies',[]),
                            'market_structure':result.get('market_structure')})
        except Exception as exc:
            errors.append({'symbol':symbol,'timeframe':tf,'reason':str(exc)})
    results.sort(key=lambda r:(r['data_status']!='OK',r['signal']=='WAIT',r['symbol'],r['timeframe']))
    return {'provider':provider.name,'timestamp':datetime.fromtimestamp(when,timezone.utc).isoformat(),
            'results':results,'errors':errors}
