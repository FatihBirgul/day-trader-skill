"""Forex extensions. Legacy stock modules remain importable and unchanged."""
from __future__ import annotations
import importlib.util
import math
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
from .sessions import session_snapshot

ROOT = Path(__file__).resolve().parent.parent

def legacy(folder, filename):
    path = ROOT / folder / filename
    spec = importlib.util.spec_from_file_location(folder.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

scanner = legacy('trader-scanner', 'scan.py')
entry = legacy('trader-entry', 'entry.py')
exit_planner = legacy('trader-exit', 'exit.py')
timemachine = legacy('trader-timemachine', 'timemachine.py')

TIMEFRAMES = {'M5': 300, 'M15': 900, 'M30': 1800, 'H1': 3600, 'H4': 14400, 'D1': 86400}
SYMBOLS = ('XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY')

class DataError(ValueError):
    pass

def finite(value, name):
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise DataError(f'{name} missing or invalid')
    if not math.isfinite(n):
        raise DataError(f'{name} must be finite')
    return n

def ema(values, n):
    if len(values) < n:
        return None
    result = sum(values[:n]) / n
    for v in values[n:]:
        result += (v - result) * (2 / (n + 1))
    return result

def atr(bars, n=14):
    if len(bars) < n + 1:
        return None
    # Reuse the exit skill's true-range calculation on broker OHLC.
    converted = [{'h': b['high'], 'l': b['low'], 'c': b['close']} for b in bars]
    value, count = exit_planner.atr_of(converted, n)
    return value if count == n else None

def ema_series(values, n):
    if len(values)<n: return []
    current=sum(values[:n])/n
    out=[current]
    alpha=2/(n+1)
    for value in values[n:]:
        current+=(value-current)*alpha
        out.append(current)
    return out

def indicators(bars):
    closes = [b['close'] for b in bars]
    if len(closes) < 200:
        raise DataError('at least 200 closed candles required')
    e12, e26 = ema_series(closes,12), ema_series(closes,26)
    macd_series = [a-b for a,b in zip(e12[14:],e26)]
    macd_line = macd_series[-1]
    signal = ema(macd_series,9)
    mid = sum(closes[-20:])/20
    std = (sum((x-mid)**2 for x in closes[-20:])/20)**.5
    previous_signal=ema(macd_series[:-1],9)
    previous_hist=macd_series[-2]-previous_signal
    histogram=macd_line-signal
    sma20=mid;sma50=sum(closes[-50:])/50
    high=max(b['high'] for b in bars[-21:-1]);low=min(b['low'] for b in bars[-21:-1])
    previous_high=max(b['high'] for b in bars[-41:-21]);previous_low=min(b['low'] for b in bars[-41:-21])
    return {'ema9':ema(closes,9),'ema20':ema(closes,20),'ema50':ema(closes,50),
            'ema100':ema(closes,100),'ema200':ema(closes,200),'sma20':sma20,'sma50':sma50,
            'rsi14':scanner.rsi(closes),'atr14':atr(bars),'normalized_atr':atr(bars)/closes[-1],
            'macd':macd_line,'macd_signal':signal,'macd_histogram':histogram,
            'momentum_change':histogram-previous_hist,
            'bollinger_upper':mid+2*std,'bollinger_lower':mid-2*std,
            'bollinger_width':4*std/mid if mid>0 else None,
            'swing_high':high,'swing_low':low,
            'higher_high':high>previous_high,'higher_low':low>previous_low,
            'lower_high':high<previous_high,'lower_low':low<previous_low,
            'ema20_slope':ema(closes,20)-ema(closes[:-1],20),
            'price_ema20_distance':(closes[-1]-ema(closes,20))/closes[-1]}

def validate_bars(bars, tf, now):
    if tf not in TIMEFRAMES:
        raise DataError('invalid timeframe')
    if not bars:
        raise DataError('no candles')
    end = 0
    for b in bars:
        t = finite(b.get('time'),'candle time')
        if t <= end or t+TIMEFRAMES[tf] > now:
            raise DataError('candles must be ordered and closed')
        end = t
        o,h,l,c = (finite(b.get(k),k) for k in ('open','high','low','close'))
        if l <= 0 or l > min(o,c) or h < max(o,c):
            raise DataError('invalid OHLC')
    return end

def price_round(value, tick, mode='nearest'):
    q = Decimal(str(value))/Decimal(str(tick))
    if mode == 'down': q = q.to_integral_value(rounding=ROUND_FLOOR)
    elif mode == 'up': q = (-q).to_integral_value(rounding=ROUND_FLOOR)*-1
    else: q = q.to_integral_value()
    return float(q*Decimal(str(tick)))

def size_lots(balance, risk_pct, entry_price, stop, meta, calc_profit=None, side='BUY', account_currency=None):
    """Size on the broker volume grid, always verifying a loss in account currency."""
    balance, risk_pct = finite(balance, 'balance'), finite(risk_pct, 'risk percent')
    if balance <= 0 or not 0 < risk_pct <= 5:
        raise DataError('invalid balance or risk percent')
    tick = finite(meta.get('tick_size'), 'tick_size')
    step = finite(meta.get('volume_step'), 'volume_step')
    minimum = finite(meta.get('volume_min'), 'volume_min')
    maximum = finite(meta.get('volume_max'), 'volume_max')
    contract = finite(meta.get('contract_size'), 'contract_size')
    if min(tick, step, minimum, maximum, contract) <= 0 or maximum < minimum:
        raise DataError('invalid contract metadata')
    currency = account_currency or meta.get('account_currency')
    if not currency or (meta.get('account_currency') and currency != meta['account_currency']):
        raise DataError('account currency unavailable or mismatched')
    ep, sl = finite(entry_price, 'entry'), finite(stop, 'stop')
    if ep <= 0 or sl <= 0 or side not in ('BUY', 'SELL') or (ep-sl)*(1 if side == 'BUY' else -1) <= 0:
        raise DataError('stop is on wrong side of entry')
    if abs(ep-sl) < tick:
        raise DataError('stop distance below tick size')
    if calc_profit:
        sample = finite(calc_profit(side, minimum, ep, sl), 'broker profit')
        if sample >= 0:
            raise DataError('broker did not report a stop-loss loss')
        per_lot = -sample / minimum
    else:
        value = finite(meta.get('tick_value'), 'tick_value')
        if value <= 0 or meta.get('tick_value_currency') != currency:
            raise DataError('tick value not verified in account currency')
        per_lot = abs(ep-sl)/tick*value
    if per_lot <= 0:
        raise DataError('estimated loss unavailable')
    cap = Decimal(str(balance))*Decimal(str(risk_pct))/Decimal('100')
    dmin, dstep, dmax = map(lambda x: Decimal(str(x)), (minimum, step, maximum))
    if Decimal(str(per_lot))*dmin > cap:
        raise DataError('minimum lot exceeds risk budget')
    upper = min(dmax, cap/Decimal(str(per_lot)))
    units = ((upper-dmin)/dstep).to_integral_value(rounding=ROUND_FLOOR)
    lots = dmin + units*dstep
    if lots < dmin or lots > dmax:
        raise DataError('volume grid unavailable')
    loss = -finite(calc_profit(side, float(lots), ep, sl), 'broker profit') if calc_profit else float(lots)*per_lot
    if loss <= 0 or Decimal(str(loss)) > cap:
        raise DataError('broker loss exceeds risk budget')
    return {'lots':float(lots),'estimated_risk':round(loss,2),'risk_cap':round(float(cap),2),'currency':currency}

def risk_check(plan, meta, max_spread, min_rr=1.5, max_open_positions=1, open_positions=0):
    reasons=[]
    try:
        if plan['direction'] not in ('BUY','SELL'): reasons.append('invalid direction')
        spread=finite(meta.get('spread'),'spread')
        if spread < 0 or spread > max_spread: reasons.append('spread exceeds limit')
        if open_positions >= max_open_positions: reasons.append('position limit reached')
        e,s,t = [finite(plan[k],k) for k in ('entry','stop_loss','take_profit_1')]
        sign = 1 if plan['direction']=='BUY' else -1
        if (e-s)*sign <= 0 or (t-e)*sign <= 0: reasons.append('invalid stop or target side')
        elif (t-e)*sign/((e-s)*sign) < min_rr: reasons.append('reward/risk below minimum')
        if abs(e-s) < finite(meta.get('stops_level',0),'stops_level')*finite(meta.get('point'),'point'):
            reasons.append('broker minimum stop distance')
    except (KeyError,DataError) as exc:
        reasons.append(str(exc))
    return {'decision':'BLOCK' if reasons else 'PASS','reasons':reasons}

def analyze(provider, symbol, timeframe='M15', balance=None, risk_pct=1.0, now=None):
    if symbol not in SYMBOLS: raise DataError('unsupported symbol')
    if timeframe not in TIMEFRAMES: raise DataError('invalid timeframe')
    now = now or datetime.now(timezone.utc).timestamp()
    base={'symbol':symbol,'timeframe':timeframe,'provider':provider.name,'timestamp':datetime.fromtimestamp(now,timezone.utc).isoformat(), 'signal':'WAIT','plan':None,'reasons':[]}
    try:
        meta=provider.metadata(symbol)
        quote=provider.quote(symbol)
        if not meta or not quote: raise DataError('quote or metadata unavailable')
        session=session_snapshot(datetime.fromtimestamp(now,timezone.utc), symbol, meta.get('trade_allowed'), meta.get('broker_hours'))
        base['session']=session
        if session['broker']['status'] not in ('OPEN','CLOSING_SOON'):
            raise DataError('broker market '+session['broker']['status'].lower())
        bid,ask=finite(quote.get('bid'),'bid'),finite(quote.get('ask'),'ask')
        qt=finite(quote.get('time'),'tick time')
        if bid <= 0 or ask <= bid: raise DataError('invalid bid/ask')
        if now-qt > 120 or qt>now+5: raise DataError('stale tick')
        spread=ask-bid
        meta={**meta,'spread':spread}
        max_spread=finite(meta.get('max_spread'),'max_spread')
        if max_spread<=0: raise DataError('invalid max_spread')
        if spread > max_spread: raise DataError('spread exceeds limit')
        bars=provider.candles(symbol,timeframe,220)
        last=validate_bars(bars,timeframe,now)
        if now-last-TIMEFRAMES[timeframe] > TIMEFRAMES[timeframe]*2: raise DataError('stale candles')
        upper=provider.candles(symbol,'H4',220) if timeframe!='H4' else bars
        upper_last=validate_bars(upper,'H4',now)
        if now-upper_last-TIMEFRAMES['H4'] > TIMEFRAMES['H4']*2: raise DataError('stale H4 candles')
        a=indicators(bars)
        b=a if timeframe=='H4' else indicators(upper)
        close=bars[-1]['close']
        trend='BUY' if close>a['ema20']>a['ema50']>a['ema200'] else 'SELL' if close<a['ema20']<a['ema50']<a['ema200'] else 'WAIT'
        higher='BUY' if upper[-1]['close']>b['ema50']>b['ema200'] else 'SELL' if upper[-1]['close']<b['ema50']<b['ema200'] else 'WAIT'
        from .strategies import candidates, resolve
        votes=candidates(bars,a)
        decision,why=resolve(votes,higher)
        base['indicators']=a
        base['strategies']=votes
        base['reasons']=[f'trend={trend}',f'H4={higher}']+why
        if decision!='WAIT':
            tick=finite(meta.get('tick_size'),'tick_size')
            point=finite(meta.get('point'),'point')
            atrv=a['atr14']
            ep=ask if decision=='BUY' else bid
            stop_dist=max(atrv*1.5,finite(meta.get('stops_level',0),'stops_level')*point+spread+tick)
            side=1 if decision=='BUY' else -1
            stop=price_round(ep-side*stop_dist,tick,'down' if side==1 else 'up')
            risk_dist=abs(ep-stop)
            plan={'symbol':symbol,'direction':decision,'timeframe':timeframe,'entry':ep,'stop_loss':stop,
                  'take_profit_1':price_round(ep+side*2*risk_dist,tick,'up' if side==1 else 'down'),
                  'take_profit_2':price_round(ep+side*3*risk_dist,tick,'up' if side==1 else 'down'),
                  'risk_reward':2.0,'invalidation':f'closed candle beyond {stop}',
                  'timestamp':base['timestamp'],'reasons':base['reasons']}
            verdict=risk_check(plan,meta,max_spread)
            if verdict['decision']=='PASS':
                if balance is not None:
                    plan['position_size']=size_lots(balance,risk_pct,ep,stop,meta,(lambda side,lots,e,s: provider.loss_for(symbol,side,lots,e,s)) if hasattr(provider,'loss_for') else getattr(provider,'calc_profit',None),decision,meta.get('account_currency'))
                base.update(signal=decision,plan=plan)
            else: base['reasons']+=verdict['reasons']
        base['data_status']='OK'
    except DataError as exc:
        base['data_status']='STALE' if 'stale' in str(exc) else 'DATA_UNAVAILABLE'
        base['reasons']=[str(exc)]
    return base

def backtest(bars, direction, entry_price, stop, target, spread=0):
    """Replay one assumed fill at the close of bars[0], then at most one exit."""
    ep, sl, tp, cost = [finite(v, n) for v,n in ((entry_price,'entry'),(stop,'stop'),(target,'target'),(spread,'spread'))]
    if direction not in ('BUY','SELL') or not 0 <= cost < abs(ep-sl):
        raise DataError('invalid backtest parameters')
    if len(bars) < 2 or len(bars) > 10000:
        raise DataError('2..10000 candles required')
    sign = 1 if direction == 'BUY' else -1
    risk_distance = abs(ep-sl)
    if (ep-sl)*sign <= 0 or (tp-ep)*sign <= 0:
        raise DataError('invalid levels')
    previous_time = None
    for i,bar in enumerate(bars):
        hi,lo,cl = [finite(bar[k],k) for k in ('high','low','close')]
        if lo <= 0 or not lo <= cl <= hi:
            raise DataError('invalid backtest candle')
        if 'time' in bar:
            t = finite(bar['time'],'time')
            if previous_time is not None and t <= previous_time:
                raise DataError('non-monotonic candle time')
            previous_time=t
        if i == 0:
            continue
        outcome = timemachine.first_exit(hi,lo,sl,tp,direction.lower())
        if outcome:
            gross = -1.0 if outcome == 'stop' else abs(tp-ep)/risk_distance
            net = gross-cost/risk_distance
            return {'trades':1,'outcomes_r':[net],'result_r':net,'status':outcome.upper(),
                    'exit_time':bar.get('time'),'bars_evaluated':i,'max_drawdown_r':max(0,-net),
                    'policy':'stop_first','entry_assumption':'filled_at_first_bar_close'}
    last = finite(bars[-1]['close'],'close')
    return {'trades':0,'outcomes_r':[],'result_r':(last-ep)*sign/risk_distance-cost/risk_distance,
            'status':'OPEN','exit_time':None,'bars_evaluated':len(bars)-1,
            'max_drawdown_r':None,'policy':'stop_first','entry_assumption':'filled_at_first_bar_close'}
