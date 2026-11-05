"""Confirmed swing structure: a pivot exists only after right-side candles close."""
from .core import DataError, finite

def market_structure(bars,left=2,right=2,limit=100,timeframe_seconds=0):
    if left<1 or right<1 or left>10 or right>10 or limit<left+right+3:
        raise DataError('invalid swing parameters')
    if len(bars)<left+right+3: raise DataError('insufficient structure candles')
    if type(timeframe_seconds) is not int or timeframe_seconds < 0:
        raise DataError('invalid structure timeframe')
    sample=bars[-limit:]
    previous=-1
    for bar in sample:
        t=finite(bar.get('time'),'time')
        if t<=previous: raise DataError('non-monotonic structure candles')
        previous=t
    highs=[];lows=[]
    for i in range(left,len(sample)-right):
        b=sample[i]
        h=finite(b['high'],'high');lo=finite(b['low'],'low')
        if all(h>finite(sample[j]['high'],'high') for j in range(i-left,i+right+1) if j!=i):
            highs.append({'price':h,'detected_at':b['time'],
                          'formed_at':b['time']+timeframe_seconds,
                          'first_detectable_at':sample[i+right]['time']+timeframe_seconds,
                          'confirmed_at':sample[i+right]['time']+timeframe_seconds,
                          'price_range':{'low':h,'high':h}, 'invalidation':h,
                          'rule_version':'strict-pivot-2-sided-1','evidence_category':'structure',
                          '_index':i})
        if all(lo<finite(sample[j]['low'],'low') for j in range(i-left,i+right+1) if j!=i):
            lows.append({'price':lo,'detected_at':b['time'],
                         'formed_at':b['time']+timeframe_seconds,
                         'first_detectable_at':sample[i+right]['time']+timeframe_seconds,
                         'confirmed_at':sample[i+right]['time']+timeframe_seconds,
                         'price_range':{'low':lo,'high':lo}, 'invalidation':lo,
                         'rule_version':'strict-pivot-2-sided-1','evidence_category':'structure',
                         '_index':i})
    trend='UNKNOWN'
    if len(highs)>=2 and len(lows)>=2:
        if highs[-1]['price']>highs[-2]['price'] and lows[-1]['price']>lows[-2]['price']:
            trend='UP'
        elif highs[-1]['price']<highs[-2]['price'] and lows[-1]['price']<lows[-2]['price']:
            trend='DOWN'
        else: trend='RANGE'
    close=finite(sample[-1]['close'],'close')
    resistance=highs[-1]['price'] if highs else None
    support=lows[-1]['price'] if lows else None
    unbroken_high=highs and all(b['close']<=resistance for b in sample[highs[-1]['_index']+right+1:-1])
    unbroken_low=lows and all(b['close']>=support for b in sample[lows[-1]['_index']+right+1:-1])
    break_direction='BUY' if resistance is not None and close>resistance and unbroken_high else \
                    'SELL' if support is not None and close<support and unbroken_low else None
    change_of_character=(trend=='DOWN' and break_direction=='BUY') or \
                        (trend=='UP' and break_direction=='SELL')
    for pivot in highs+lows: pivot.pop('_index')
    return {'trend':trend,'support':support,'resistance':resistance,
            'rule_version':'forex-structure-2','evidence_category':'structure',
            'break_confirmed_at':sample[-1]['time']+timeframe_seconds if break_direction else None,
            'break_of_structure':break_direction,'change_of_character':change_of_character,
            'last_high':highs[-1] if highs else None,'last_low':lows[-1] if lows else None,
            'confirmed_highs':len(highs),'confirmed_lows':len(lows)}
