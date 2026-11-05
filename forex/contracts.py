"""Public, provider independent snapshot contract. No private implementation imports."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json

from .core import DataError, SYMBOLS, TIMEFRAMES, finite, validate_bars
from .sessions import broker_status

SCHEMA_VERSION = 'forex-snapshot-1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


@dataclass(frozen=True)
class Snapshot:
    """Serialized ownership prevents nested mutable aliases crossing engine boundaries."""
    snapshot_id: str
    payload_json: str

    def payload(self):
        return json.loads(self.payload_json)


def _bars(rows, timeframe, as_of, metadata):
    if not isinstance(rows, (list, tuple)) or not 200 <= len(rows) <= 256:
        raise DataError('insufficient or excessive closed candles')
    result = []
    duration = TIMEFRAMES[timeframe]
    for raw in rows:
        if not isinstance(raw, dict):
            raise DataError('invalid candle')
        t = raw.get('time')
        if isinstance(t, bool) or not isinstance(t, int) or t <= 0:
            raise DataError('integer UTC candle time required')
        if raw.get('is_final', True) is not True:
            raise DataError('unfinished candle')
        bar = {'time': t, 'open_time_utc': t, 'close_time_utc': t + duration,
               'is_final': True, 'timeframe': timeframe}
        for name in ('open', 'high', 'low', 'close'):
            if isinstance(raw.get(name), bool):
                raise DataError('boolean candle price')
            bar[name] = finite(raw.get(name), name)
        kind = raw.get('volume_kind', 'tick' if 'tick_volume' in raw else 'unavailable')
        if kind not in ('real', 'tick', 'unavailable'):
            raise DataError('invalid volume kind')
        if kind == 'real':
            raise DataError('centralized real volume unavailable for Forex/metal analysis')
        volume = raw.get('tick_volume', raw.get('volume')) if kind == 'tick' else None
        if kind == 'tick':
            if isinstance(volume, bool) or finite(volume, 'tick volume') < 0:
                raise DataError('invalid tick volume')
            volume = float(volume)
        elif raw.get('volume') is not None:
            raise DataError('unavailable volume must be null')
        bar.update(volume_kind=kind, volume=volume)
        if result:
            gap = t - result[-1]['close_time_utc']
            if gap < 0 or gap % duration:
                raise DataError('overlapping or misaligned candles')
            if gap > duration * 500:
                raise DataError('candle gap exceeds validation budget')
            # Missing observations are allowed only when the explicit broker
            # schedule says CLOSED for the entire missing interval (minute grid).
            for missing in range(result[-1]['close_time_utc'], t, 60):
                status = broker_status(datetime.fromtimestamp(missing, timezone.utc), '',
                                       metadata.get('trade_allowed'), metadata.get('broker_hours'))
                if status['status'] != 'CLOSED':
                    raise DataError('missing candle during open or unknown broker hours')
        result.append(bar)
    validate_bars(result, timeframe, as_of)
    if as_of - result[-1]['close_time_utc'] > duration * 2:
        raise DataError('stale candles')
    return result


def capture(provider, symbol, timeframe, as_of, confirmations=('H4',)):
    if symbol not in SYMBOLS or timeframe not in TIMEFRAMES:
        raise DataError('unsupported symbol or timeframe')
    if not confirmations or len(confirmations) > 3 or len(set(confirmations)) != len(confirmations):
        raise DataError('invalid confirmation timeframes')
    if any(tf not in TIMEFRAMES or TIMEFRAMES[tf] < TIMEFRAMES[timeframe] for tf in confirmations):
        raise DataError('confirmation timeframe must be equal or higher')
    as_of = finite(as_of, 'as of')
    # Providers remain the only I/O boundary. Each resource is read once.
    meta, quote = provider.metadata(symbol), provider.quote(symbol)
    if not isinstance(meta, dict) or not isinstance(quote, dict):
        raise DataError('quote or metadata unavailable')
    if meta.get('symbol', symbol) != symbol or quote.get('symbol', symbol) != symbol:
        raise DataError('instrument identity mismatch')
    if not isinstance(provider.name, str) or not provider.name:
        raise DataError('provider identity required')
    bid, ask, quote_time = (finite(quote.get(k), k) for k in ('bid', 'ask', 'time'))
    if bid <= 0 or ask <= bid:
        raise DataError('invalid bid/ask')
    if as_of - quote_time > 120 or quote_time > as_of + 5:
        raise DataError('stale tick')
    quote = {**quote, 'bid': bid, 'ask': ask, 'time': quote_time}
    primary = _bars(provider.candles(symbol, timeframe, 256), timeframe, as_of, meta)
    primary_close = primary[-1]['close_time_utc']
    frames = {timeframe: primary}
    for tf in confirmations:
        if tf == timeframe:
            continue
        rows = provider.candles(symbol, tf, 256)
        # Higher frames are intentionally viewed at the primary decision close.
        # Invalid/non-integer timestamps must not disappear through this cut.
        if any(not isinstance(b, dict) or type(b.get('time')) is not int for b in rows):
            raise DataError('invalid confirmation candle time')
        rows = [b for b in rows if b['time'] + TIMEFRAMES[tf] <= primary_close]
        frames[tf] = _bars(rows, tf, primary_close, meta)
    body = {'schema_version': SCHEMA_VERSION, 'symbol': symbol,
            'broker_symbol': meta.get('broker_symbol', symbol),
            'market_type': meta.get('market_type', 'unverified'),
            'contract_type': meta.get('contract_type', 'unverified'),
            'venue': meta.get('broker_server', meta.get('venue', 'unverified')),
            'price_kind': meta.get('price_kind', 'bid'), 'provider': provider.name,
            'data_version': meta.get('data_version', 'provider-unversioned'),
            'timeframe': timeframe, 'as_of_utc': as_of,
            'decision_close_utc': primary_close, 'confirmations': list(confirmations),
            'metadata': meta, 'quote': quote, 'frames': frames, 'qc_flags': []}
    if body['price_kind'] != 'bid':
        raise DataError('live planning requires bid candles')
    if body['market_type'] not in ('forex_spot', 'gold_spot', 'cfd', 'unverified'):
        raise DataError('unsupported market identity')
    serialized = canonical(body)
    return Snapshot(hashlib.sha256(serialized.encode()).hexdigest(), serialized)


class SnapshotProvider:
    """Run the existing V4 core against owned data, with no new provider reads."""
    def __init__(self, snapshot):
        self._snapshot = snapshot
        self.name = snapshot.payload()['provider']

    def metadata(self, symbol):
        return self._snapshot.payload()['metadata']

    def quote(self, symbol):
        return self._snapshot.payload()['quote']

    def candles(self, symbol, timeframe, count=220):
        return self._snapshot.payload()['frames'][timeframe][-count:]
