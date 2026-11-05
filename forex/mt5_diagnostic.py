"""Read-only Windows demo diagnostic: python -m forex.mt5_diagnostic."""
import json
from datetime import datetime,timezone
from .providers import MT5Provider
from .core import SYMBOLS, DataError

def diagnose(provider,symbols=SYMBOLS):
    report={'provider':provider.name,'timestamp':datetime.now(timezone.utc).isoformat(),
            'terminal':None,'symbols':{}}
    try: report['terminal']=provider.health()
    except DataError as exc:
        report['terminal']={'connected':False,'reason':str(exc)}
        return report
    for symbol in symbols:
        try:
            meta=provider.metadata(symbol)
            quote=provider.quote(symbol)
            bars=provider.candles(symbol,'M15',2)
            report['symbols'][symbol]={'status':'OK','broker_symbol':meta['broker_symbol'],
                'contract_size':meta['contract_size'],'tick_size':meta['tick_size'],
                'tick_value':meta['tick_value'],'account_currency':meta['account_currency'],
                'volume_min':meta['volume_min'],'volume_step':meta['volume_step'],
                'trade_allowed':meta['trade_allowed'],'last_tick_time':quote['time'],
                'last_closed_candle_time':bars[-1]['time'] if bars else None}
        except (DataError,KeyError) as exc:
            report['symbols'][symbol]={'status':'ERROR','reason':str(exc)}
    return report

def main():
    try:
        provider=MT5Provider()
        try: print(json.dumps(diagnose(provider),indent=2,allow_nan=False))
        finally: provider.close()
    except DataError as exc:
        print(json.dumps({'status':'DATA_UNAVAILABLE','reason':str(exc)}))
        return 1
    return 0

if __name__=='__main__': raise SystemExit(main())
