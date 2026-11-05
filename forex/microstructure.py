"""Explicit historical bid/mid OHLC conversion; levels are chart-price levels.

Historical MT5 bars are bid based. For a SELL, closing requires buying at ask.
No intrabar spread history is inferred: caller supplies a fixed spread assumption.
"""
from .core import DataError, finite, timemachine

def executable_prices(direction, chart_entry, stop, target, spread, basis='bid', slippage=0):
    if basis not in ('bid','mid'): raise DataError('unknown candle price basis')
    if direction not in ('BUY','SELL'): raise DataError('invalid direction')
    e,s,t,w,slip=[finite(v,k) for v,k in ((chart_entry,'entry'),(stop,'stop'),(target,'target'),(spread,'spread'),(slippage,'slippage'))]
    if min(e,s,t)<=0 or w<0 or slip<0: raise DataError('invalid price or cost')
    offset=w/2 if basis=='mid' else 0
    bid_entry=e-offset
    actual_entry=bid_entry+(w+slip if direction=='BUY' else -slip)
    sign=1 if direction=='BUY' else -1
    stop_bid=s-offset; target_bid=t-offset
    stop_exit=stop_bid if sign==1 else stop_bid+w
    target_exit=target_bid if sign==1 else target_bid+w
    risk=(actual_entry-stop_exit)*sign
    reward=(target_exit-actual_entry)*sign
    if risk<=0 or reward<=0: raise DataError('invalid executable stop or target')
    return {'entry':actual_entry,'stop_exit':stop_exit,'target_exit':target_exit,
            'risk':risk,'reward':reward,'bid_entry':bid_entry,'stop_bid':stop_bid,
            'target_bid':target_bid,'spread':w,'basis':basis,'direction':direction}

def exit_on_bar(model,bar,slippage=0,commission=0):
    """Return None or one conservative exit with net R. Same-bar stop wins."""
    w=model['spread'];offset=w/2 if model['basis']=='mid' else 0
    high=finite(bar['high'],'high')-offset;low=finite(bar['low'],'low')-offset
    op=finite(bar['open'],'open')-offset
    outcome=timemachine.first_exit(high,low,model['stop_bid'],model['target_bid'],model['direction'].lower())
    if not outcome: return None
    sign=1 if model['direction']=='BUY' else -1
    if outcome=='stop':
        adverse_open=op if sign==1 else op+w
        exit_price=min(model['stop_exit'],adverse_open) if sign==1 else max(model['stop_exit'],adverse_open)
    else: exit_price=model['target_exit']
    extra=finite(slippage,'slippage')+finite(commission,'commission')
    if extra<0: raise DataError('negative exit cost')
    gross=(exit_price-model['entry'])*sign
    return {'outcome':outcome,'exit_price':exit_price,'net_r':(gross-extra)/model['risk']}
