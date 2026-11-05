"""Read-only MT5 and explicitly labelled fixture data providers."""
from __future__ import annotations
import threading
from datetime import datetime, timezone
from .core import DataError, SYMBOLS, TIMEFRAMES

class FixtureProvider:
    name='fixture-test-only'
    def __init__(self, data): self.data=data
    def metadata(self,symbol): return self.data[symbol]['metadata']
    def quote(self,symbol): return self.data[symbol]['quote']
    def candles(self,symbol,timeframe,count=220): return self.data[symbol]['candles'][timeframe][-count:]
    def calc_profit(self,side,lots,entry,stop):
        m=self.data[next(iter(self.data))]['metadata']
        return (stop-entry)*(1 if side=='BUY' else -1)*lots*m['tick_value']/m['tick_size']

class MT5Provider:
    name='mt5'
    def __init__(self, mt5=None, mappings=None):
        if mt5 is None:
            try: import MetaTrader5 as mt5
            except ImportError: raise DataError('MetaTrader5 package unavailable; Windows terminal required')
        self.mt5=mt5; self.lock=threading.RLock(); self.mappings=mappings or {}
        self.connected=False
    def connect(self):
        with self.lock:
            if not self.connected:
                if not self.mt5.initialize(): raise DataError(f'MT5 initialize failed: {self.mt5.last_error()}')
                self.connected=True
    def close(self):
        with self.lock:
            if self.connected: self.mt5.shutdown(); self.connected=False
    def _symbol(self, symbol):
        if symbol not in SYMBOLS: raise DataError('unsupported symbol')
        self.connect()
        actual=self.mappings.get(symbol,symbol)
        info=self.mt5.symbol_info(actual)
        if info is None or not (actual.upper().startswith(symbol) or actual.upper().endswith(symbol)):
            raise DataError('broker symbol mapping unverified')
        if not self.mt5.symbol_select(actual,True): raise DataError('symbol_select failed')
        return actual,info
    def metadata(self,symbol):
        with self.lock:
            actual,i=self._symbol(symbol)
            account=self.mt5.account_info()
            return {'symbol':symbol,'broker_symbol':actual,'contract_size':i.trade_contract_size,
                    'tick_size':i.trade_tick_size,'tick_value':i.trade_tick_value,
                    'point':i.point,'volume_min':i.volume_min,'volume_max':i.volume_max,
                    'volume_step':i.volume_step,'stops_level':i.trade_stops_level,
                    'account_currency':getattr(account,'currency',None),
                    'tick_value_currency':getattr(account,'currency',None) if account else None}
    def quote(self,symbol):
        with self.lock:
            actual,_=self._symbol(symbol); t=self.mt5.symbol_info_tick(actual)
            if t is None: raise DataError('tick unavailable')
            return {'symbol':symbol,'bid':t.bid,'ask':t.ask,'time':t.time_msc/1000 if getattr(t,'time_msc',0) else t.time}
    def candles(self,symbol,timeframe,count=220):
        if timeframe not in TIMEFRAMES: raise DataError('invalid timeframe')
        if not 1<=count<=10000: raise DataError('invalid candle count')
        with self.lock:
            actual,_=self._symbol(symbol)
            tf=getattr(self.mt5,'TIMEFRAME_'+timeframe)
            rows=self.mt5.copy_rates_from_pos(actual,tf,0,count+1)
            if rows is None: raise DataError('candles unavailable')
            now=datetime.now(timezone.utc).timestamp()
            # MT5 bar timestamp marks the OPEN; omit current unfinished bar.
            return [{'time':int(r['time']),'open':float(r['open']),'high':float(r['high']),
                     'low':float(r['low']),'close':float(r['close']),'tick_volume':int(r['tick_volume'])}
                    for r in rows if int(r['time'])+TIMEFRAMES[timeframe]<=now][-count:]
    def calc_profit(self,side,lots,entry,stop):
        with self.lock:
            order_type=self.mt5.ORDER_TYPE_BUY if side=='BUY' else self.mt5.ORDER_TYPE_SELL
            # The symbol is selected by the caller's metadata/quote request.
            raise DataError('symbol argument required for MT5 profit calculation')
    def loss_for(self,symbol,side,lots,entry,stop):
        with self.lock:
            actual,_=self._symbol(symbol)
            typ=self.mt5.ORDER_TYPE_BUY if side=='BUY' else self.mt5.ORDER_TYPE_SELL
            result=self.mt5.order_calc_profit(typ,actual,lots,entry,stop)
            if result is None: raise DataError('order_calc_profit failed')
            return result
