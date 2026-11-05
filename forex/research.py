"""Bounded chronological research backtest; not an execution or forecasting engine."""
from datetime import datetime,timezone
import random
from .core import DataError, finite, indicators, price_round, timemachine
from .strategies import candidates,resolve

def strategy_backtest(bars, spread, commission=0, slippage=0, holdout=0.25, seed=19):
    """Generate on closed bar i; assume fill at open i+1; one position at a time."""
    n=len(bars)
    if not 220<=n<=2000 or not 0<holdout<.5:
        raise DataError('220..2000 candles and holdout between 0 and 0.5 required')
    costs=[finite(x,k) for x,k in ((spread,'spread'),(commission,'commission'),(slippage,'slippage'))]
    if any(x<0 for x in costs): raise DataError('negative trading cost')
    previous=0
    for bar in bars:
        t=finite(bar.get('time'),'time')
        if t<=previous: raise DataError('candles must be time ordered')
        previous=t
        lo,hi=finite(bar.get('low'),'low'),finite(bar.get('high'),'high')
        o,c=finite(bar.get('open'),'open'),finite(bar.get('close'),'close')
        if lo<=0 or lo>min(o,c) or hi<max(o,c): raise DataError('invalid OHLC')
    trades=[];position=None;split=int(n*(1-holdout));exposure=0
    for i in range(200,n):
        bar=bars[i]
        if position is None:
            metrics=indicators(bars[:i]) # only candles closed before entry bar
            votes=candidates(bars[:i],metrics)
            close=bars[i-1]['close']
            higher='BUY' if close>metrics['ema50']>metrics['ema200'] else 'SELL' if close<metrics['ema50']<metrics['ema200'] else 'WAIT'
            direction,_=resolve(votes,higher)
            if direction=='WAIT': continue
            sign=1 if direction=='BUY' else -1
            entry=bar['open']+sign*costs[0]/2+sign*costs[2]
            risk=max(metrics['atr14']*1.5,costs[0]*2)
            if risk<=0: continue
            position={'direction':direction,'entry':entry,'stop':entry-sign*risk,
                      'target':entry+sign*2*risk,'entry_time':bar['time'],
                      'entry_index':i,'strategy':[v['strategy'] for v in votes],
                      'split':'holdout' if i>=split else 'development'}
        exposure+=1
        side=position['direction'].lower()
        hit=timemachine.first_exit(bar['high'],bar['low'],position['stop'],position['target'],side)
        if not hit: continue
        risk=abs(position['entry']-position['stop'])
        # Stop first is conservative when both extremes occur in one candle.
        if hit=='stop':
            adverse_open=bar['open']-sign*costs[0]/2
            exit_price=min(position['stop'],adverse_open) if sign==1 else max(position['stop'],adverse_open)
            gross=(exit_price-position['entry'])*sign/risk
        else:
            gross=2-costs[0]/2/risk
        net=gross-(costs[1]+costs[2])/risk
        trades.append({**position,'exit_time':bar['time'],'exit_index':i,'outcome':hit,
                       'r':net,'holding_bars':i-position['entry_index']+1})
        position=None
    return {'trades':trades,'open_position':position,'metrics':_metrics(trades,exposure,n-200),
            'development':_metrics([t for t in trades if t['split']=='development'],0,0),
            'holdout':_metrics([t for t in trades if t['split']=='holdout'],0,0),
            'holdout_start_time':bars[split]['time'],
            'strategy_comparison':{name:_metrics([t for t in trades if name in t['strategy']],0,0)
                                   for name in ('trend_following','breakout','pullback')},
            'monte_carlo':_bootstrap(trades,seed),
            'policy':'stop_first','entry_assumption':'next_bar_open','seed':seed}

def _metrics(trades,exposure,bars):
    rs=[t['r'] for t in trades];count=len(rs);equity=peak=drawdown=0.0
    wins=losses=run_win=run_loss=0;max_wins=max_losses=0
    for r in rs:
        equity+=r;peak=max(peak,equity);drawdown=max(drawdown,peak-equity)
        if r>0:
            wins+=1;run_win+=1;run_loss=0;max_wins=max(max_wins,run_win)
        else:
            losses+=1;run_loss+=1;run_win=0;max_losses=max(max_losses,run_loss)
    gain=sum(x for x in rs if x>0);lost=-sum(x for x in rs if x<0)
    return {'trade_count':count,'win_rate':wins/count if count else None,
            'average_r':sum(rs)/count if count else None,'total_r':sum(rs),
            'profit_factor':gain/lost if lost else None,'max_drawdown_r':drawdown,
            'max_consecutive_wins':max_wins,'max_consecutive_losses':max_losses,
            'average_holding_bars':sum(t['holding_bars'] for t in trades)/count if count else None,
            'exposure_fraction':exposure/bars if bars else None}

def _bootstrap(trades,seed,draws=200):
    rs=[t['r'] for t in trades]
    if not rs: return {'draws':0,'seed':seed,'median_total_r':None}
    rng=random.Random(seed)
    totals=sorted(sum(rng.choice(rs) for _ in rs) for _ in range(draws))
    return {'draws':draws,'seed':seed,'median_total_r':totals[draws//2]}
