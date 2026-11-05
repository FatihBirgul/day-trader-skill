"""Bounded chronological research backtest; not an execution or forecasting engine."""
from datetime import datetime,timezone
import random
import hashlib,json
from .core import DataError, finite, indicators, price_round, timemachine
from .strategies import candidates,resolve
from .microstructure import executable_prices, exit_on_bar

def strategy_backtest(bars, spread, commission=0, slippage=0, holdout=0.25, seed=19, price_basis='bid', strategy=None, compare=True,
                      evaluation_start=200):
    """Generate on closed bar i; assume fill at open i+1; one position at a time."""
    n=len(bars)
    if strategy not in (None,'trend_following','breakout','pullback'):
        raise DataError('unknown strategy')
    if price_basis not in ('bid','mid'): raise DataError('unknown candle price basis')
    if not 220<=n<=2000 or not 0<holdout<.5:
        raise DataError('220..2000 candles and holdout between 0 and 0.5 required')
    if type(evaluation_start) is not int or not 200 <= evaluation_start < n:
        raise DataError('invalid evaluation start')
    costs=[finite(x,k) for x,k in ((spread,'spread'),(commission,'commission'),(slippage,'slippage'))]
    if any(x<0 for x in costs): raise DataError('negative trading cost')
    previous=0
    for bar in bars:
        if type(bar.get('time')) is not int or bar.get('is_final',True) is not True:
            raise DataError('integer timestamp and closed candles required')
        t=finite(bar.get('time'),'time')
        if t<=previous: raise DataError('candles must be time ordered')
        previous=t
        lo,hi=finite(bar.get('low'),'low'),finite(bar.get('high'),'high')
        o,c=finite(bar.get('open'),'open'),finite(bar.get('close'),'close')
        if lo<=0 or lo>min(o,c) or hi<max(o,c): raise DataError('invalid OHLC')
    trades=[];position=None;model=None;split=int(n*(1-holdout));exposure=0
    for i in range(evaluation_start,n):
        bar=bars[i]
        if position is None:
            metrics=indicators(bars[:i]) # only candles closed before entry bar
            votes=candidates(bars[:i],metrics)
            if strategy is not None: votes=[v for v in votes if v['strategy']==strategy]
            close=bars[i-1]['close']
            higher='BUY' if close>metrics['ema50']>metrics['ema200'] else 'SELL' if close<metrics['ema50']<metrics['ema200'] else 'WAIT'
            direction,_=resolve(votes,higher)
            if direction=='WAIT': continue
            sign=1 if direction=='BUY' else -1
            distance=max(metrics['atr14']*1.5,costs[0]*2)
            if distance<=0: continue
            chart_stop=bar['open']-sign*distance
            chart_target=bar['open']+sign*2*distance
            try: model=executable_prices(direction,bar['open'],chart_stop,chart_target,
                                          costs[0],price_basis,costs[2])
            except DataError: continue
            position={'direction':direction,'entry':model['entry'],'stop':chart_stop,
                      'target':chart_target,'entry_time':bar['time'],'entry_index':i,
                      'strategy':[v['strategy'] for v in votes]}
        exposure+=1
        result=exit_on_bar(model,bar,costs[2],costs[1])
        if not result: continue
        trades.append({**position,'exit_time':bar['time'],'exit_index':i,
                       'outcome':result['outcome'],'exit_price':result['exit_price'],
                       'r':result['net_r'],'holding_bars':i-position['entry_index']+1})
        position=None
    comparisons={}
    if compare and strategy is None:
        for name in ('trend_following','breakout','pullback'):
            separate=strategy_backtest(bars,spread,commission,slippage,holdout,seed,price_basis,
                                       strategy=name,compare=False,evaluation_start=evaluation_start)
            comparisons[name]={'metrics':separate['metrics'],'trades':separate['trades']}
    dataset_hash=hashlib.sha256(json.dumps(bars,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return {'trades':trades,'open_position':position,'metrics':_metrics(trades,exposure,n-evaluation_start),
            'development':_metrics([t for t in trades if t['entry_index']<split],0,0),
            'development_completed_before_holdout':_metrics([t for t in trades if t['exit_index']<split],0,0),
            'boundary_crossing_trades':[t for t in trades if t['entry_index']<split<=t['exit_index']],
            'holdout':_metrics([t for t in trades if t['entry_index']>=split],0,0),
            'holdout_start_time':bars[split]['time'],
            'strategy_comparison':comparisons,
            'monte_carlo':_bootstrap(trades,seed),
            'policy':'stop_first','entry_assumption':'next_bar_open','price_basis':price_basis,
            'spread_assumption':spread,'seed':seed,'evaluation_start_index':evaluation_start,
            'dataset_sha256':dataset_hash,'strategy_version':'forex-v4-1',
            'cost_units':'spread/slippage/commission in price units per unit exposure',
            'validation_status':'MECHANICS_ONLY','forward_validated':False,
            'warning':'Entry-partition development may include boundary-crossing labels; use completed-before-holdout for isolated labels. Source/license and finality are caller declarations.'}

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
    curve=[];running=0
    for r in rs:
        running+=r;curve.append(running)
    return {'trade_count':count,'win_rate':wins/count if count else None,'equity_curve_r':[0.0]+curve,
            'average_r':sum(rs)/count if count else None,'total_r':sum(rs),
            'profit_factor':gain/lost if lost else None,'max_drawdown_r':drawdown,
            'max_consecutive_wins':max_wins,'max_consecutive_losses':max_losses,
            'average_holding_bars':sum(t['holding_bars'] for t in trades)/count if count else None,
            'exposure_fraction':exposure/bars if bars else None}

def _bootstrap(trades,seed,draws=200):
    """Empirical return bootstrap; no predictive probability claim."""
    rs=[t['r'] for t in trades]
    if not rs:
        return {'draws':0,'seed':seed,'sample_size':0,'method':'trade_return_bootstrap',
                'median_total_r':None,'p5_total_r':None,'p95_total_r':None,
                'median_drawdown_r':None,'worst_drawdown_r':None,
                'median_max_losing_streak':None,'p5_drawdown_r':None,'p95_drawdown_r':None,
                'p95_max_losing_streak':None,'warning':'no closed trade sample'}
    rng=random.Random(seed)
    totals=[];drawdowns=[];streaks=[]
    for _ in range(draws):
        equity=peak=dd=0.0;streak=max_streak=0
        for _ in rs:
            r=rng.choice(rs)
            equity+=r;peak=max(peak,equity);dd=max(dd,peak-equity)
            streak=streak+1 if r<0 else 0
            max_streak=max(max_streak,streak)
        totals.append(equity);drawdowns.append(dd);streaks.append(max_streak)
    totals.sort();drawdowns.sort();streaks.sort()
    return {'draws':draws,'seed':seed,'sample_size':len(rs),'method':'trade_return_bootstrap',
            'median_total_r':totals[draws//2],
            'p5_total_r':totals[int(.05*(draws-1))],
            'p95_total_r':totals[int(.95*(draws-1))],
            'median_drawdown_r':drawdowns[draws//2],
            'p5_drawdown_r':drawdowns[int(.05*(draws-1))],
            'p95_drawdown_r':drawdowns[int(.95*(draws-1))],
            'worst_drawdown_r':drawdowns[-1],
            'median_max_losing_streak':streaks[draws//2],
            'p95_max_losing_streak':streaks[int(.95*(draws-1))],
            'warning':'small empirical sample; not a profitability probability' if len(rs)<30 else 'empirical bootstrap; not a profitability probability'}

def walk_forward(bars, spread, folds=3, **kwargs):
    """Fixed-rule rolling evaluation; no parameter fitting or optimization."""
    if not 2<=folds<=5 or len(bars)<220+folds*20:
        raise DataError('insufficient candles for 2..5 rolling folds')
    span=(len(bars)-220)//folds
    windows=[]
    for fold in range(folds):
        start=220+fold*span
        end=220+(fold+1)*span if fold<folds-1 else len(bars)
        result=strategy_backtest(bars[:end],spread,compare=False,evaluation_start=start,**kwargs)
        trades=[t for t in result['trades'] if start<=t['entry_index']<end]
        windows.append({'fold':fold+1,'train_end_index':start-1,'test_start_index':start,
                        'test_end_index':end-1,'metrics':_metrics(trades,0,0),
                        'trades':trades})
    return {'folds':windows,'method':'fixed_rules_rolling_evaluation',
            'warning':'No parameter fitting; not proof of out-of-sample edge'}
