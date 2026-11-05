"""Read-only MT5 and explicitly labelled fixture data providers."""
from __future__ import annotations
import threading
import os
import json
from datetime import datetime, timezone
from .core import DataError, SYMBOLS, TIMEFRAMES, finite, validate_bars

class FixtureProvider:
    name='fixture-test-only'
    def __init__(self, data): self.data=data
    def metadata(self,symbol): return self.data[symbol]['metadata']
    def quote(self,symbol): return self.data[symbol]['quote']
    def candles(self,symbol,timeframe,count=220): return self.data[symbol]['candles'][timeframe][-count:]
    def loss_for(self,symbol,side,lots,entry,stop):
        m=self.metadata(symbol)
        return (stop-entry)*(1 if side=='BUY' else -1)*lots*m['tick_value']/m['tick_size']

class MT5Provider:
    name='mt5'
    def __init__(self, mt5=None, mappings=None):
        if mt5 is None:
            try: import MetaTrader5 as mt5
            except ImportError: raise DataError('MetaTrader5 package unavailable; Windows terminal required')
        if mappings is None:
            raw=os.environ.get('MT5_SYMBOL_MAP','{}')
            try: mappings=json.loads(raw)
            except json.JSONDecodeError: raise DataError('MT5_SYMBOL_MAP must be JSON')
            if not isinstance(mappings,dict) or any(k not in SYMBOLS or not isinstance(v,str) for k,v in mappings.items()):
                raise DataError('invalid MT5_SYMBOL_MAP')
        raw_hours=os.environ.get('MT5_BROKER_HOURS','{}')
        try: self.hours=json.loads(raw_hours)
        except json.JSONDecodeError: raise DataError('MT5_BROKER_HOURS must be JSON')
        if not isinstance(self.hours,dict): raise DataError('invalid MT5_BROKER_HOURS')
        self.mt5=mt5; self.lock=threading.RLock(); self.mappings=mappings
        self.connected=False
    def connect(self):
        with self.lock:
            if self.connected and hasattr(self.mt5, 'terminal_info'):
                terminal = self.mt5.terminal_info()
                if terminal is None or not getattr(terminal, 'connected', False):
                    self.mt5.shutdown()
                    self.connected = False
            if not self.connected:
                if not self.mt5.initialize(): raise DataError(f'MT5 initialize failed: {self.mt5.last_error()}')
                self.connected=True
    def health(self):
        with self.lock:
            self.connect()
            terminal = self.mt5.terminal_info() if hasattr(self.mt5, 'terminal_info') else None
            if terminal is None or not getattr(terminal, 'connected', False):
                raise DataError('MT5 terminal disconnected')
            return {'connected':True,'trade_allowed':bool(getattr(terminal,'trade_allowed',False))}
    def close(self):
        with self.lock:
            if self.connected: self.mt5.shutdown(); self.connected=False
    def _symbol(self, symbol):
        if symbol not in SYMBOLS: raise DataError('unsupported symbol')
        self.connect()
        actual=self.mappings.get(symbol,symbol)
        info=self.mt5.symbol_info(actual)
        if info is None or not actual or not isinstance(actual,str):
            raise DataError('broker symbol mapping unverified')
        # An alias is trusted only when explicitly configured and resolves to an exact MT5 name.
        if actual != symbol and self.mappings.get(symbol) != actual:
            raise DataError('broker symbol mapping unverified')
        if not self.mt5.symbol_select(actual,True): raise DataError('symbol_select failed')
        return actual,info
    def metadata(self,symbol):
        with self.lock:
            actual,i=self._symbol(symbol)
            account=self.mt5.account_info()
            if account is None: raise DataError('MT5 account unavailable')
            required=('trade_contract_size','trade_tick_size','trade_tick_value','point','volume_min','volume_max','volume_step','trade_stops_level')
            if any(not hasattr(i,key) for key in required): raise DataError('incomplete broker metadata')
            if any(finite(getattr(i,key),key) <= 0 for key in required[:-1]): raise DataError('invalid broker metadata')
            return {'symbol':symbol,'broker_symbol':actual,'contract_size':i.trade_contract_size,
                    'tick_size':i.trade_tick_size,'tick_value':i.trade_tick_value,
                    'point':i.point,'volume_min':i.volume_min,'volume_max':i.volume_max,
                    'volume_step':i.volume_step,'stops_level':i.trade_stops_level,
                    'trade_allowed':bool(getattr(i,'trade_mode',1)) and bool(getattr(account,'trade_allowed',True)),
                    'broker_hours':self.hours.get(symbol),
                    'account_currency':getattr(account,'currency',None),
                    'tick_value_currency':getattr(account,'currency',None) if account else None}
    def quote(self,symbol):
        with self.lock:
            actual,_=self._symbol(symbol); t=self.mt5.symbol_info_tick(actual)
            if t is None: raise DataError('tick unavailable')
            stamp=t.time_msc/1000 if getattr(t,'time_msc',0) else t.time
            bid,ask=finite(t.bid,'bid'),finite(t.ask,'ask')
            age=datetime.now(timezone.utc).timestamp()-finite(stamp,'tick time')
            if age>120 or age < -5: raise DataError('stale tick')
            if bid<=0 or ask<=bid: raise DataError('invalid bid/ask')
            return {'symbol':symbol,'bid':bid,'ask':ask,'time':stamp}
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
            try:
                result=[{'time':int(r['time']),'open':float(r['open']),'high':float(r['high']),
                         'low':float(r['low']),'close':float(r['close']),'tick_volume':int(r['tick_volume'])}
                        for r in rows if int(r['time'])+TIMEFRAMES[timeframe]<=now][-count:]
            except (KeyError,TypeError,ValueError) as exc:
                raise DataError('invalid MT5 candle data') from exc
            validate_bars(result,timeframe,now)
            return result
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
