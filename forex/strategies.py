"""Deterministic closed-candle setup rules; no order execution."""
from .core import entry, ema

STRATEGIES=('trend_following','breakout','pullback')

def candidates(bars, metrics):
    """Each strategy votes on closed candles only; conflicting votes are rejected."""
    close=bars[-1]['close'];prev=bars[-2]
    ema20_prev=ema([b['close'] for b in bars[:-1]],20)
    ema20,ema50,ema200=metrics['ema20'],metrics['ema50'],metrics['ema200']
    trend='BUY' if close>ema20>ema50>ema200 else 'SELL' if close<ema20<ema50<ema200 else 'WAIT'
    momentum='BUY' if metrics['rsi14']>50 and metrics['macd']>metrics['macd_signal'] else 'SELL' if metrics['rsi14']<50 and metrics['macd']<metrics['macd_signal'] else 'WAIT'
    breakout=entry.closed_bar_breakout([b['close'] for b in bars[-21:]],
                         [b['high'] for b in bars[-21:]], [b['low'] for b in bars[-21:]])
    votes=[]
    if trend==momentum and trend!='WAIT':
        votes.append({'strategy':'trend_following','direction':trend,'reason':'EMA alignment and RSI/MACD momentum'})
    if breakout!='WAIT' and breakout==trend:
        votes.append({'strategy':'breakout','direction':breakout,'reason':'close beyond preceding 20-bar range'})
    if trend==momentum=='BUY' and prev['low']<=ema20_prev and close>prev['high']:
        votes.append({'strategy':'pullback','direction':'BUY','reason':'EMA20 touch and closed-bar rebound'})
    if trend==momentum=='SELL' and prev['high']>=ema20_prev and close<prev['low']:
        votes.append({'strategy':'pullback','direction':'SELL','reason':'EMA20 touch and closed-bar rejection'})
    return votes

def resolve(votes, higher):
    directions={v['direction'] for v in votes}
    if len(directions)!=1 or higher not in directions:
        return 'WAIT', ['strategy conflict or higher timeframe mismatch']
    return next(iter(directions)),[v['strategy']+': '+v['reason'] for v in votes]
