"""Read-only MT5 and explicitly labelled fixture data providers."""
from __future__ import annotations
import threading
import os
import json
import copy
from datetime import datetime, timezone
from .core import DataError, SYMBOLS, TIMEFRAMES, finite, validate_bars

class FixtureProvider:
    name='fixture-test-only'
    def __init__(self, data): self.data=data
    def metadata(self,symbol):
        return copy.deepcopy({'symbol':symbol,'price_kind':'bid','source':self.name,
                              **self.data[symbol]['metadata']})
    def quote(self,symbol): return copy.deepcopy(self.data[symbol]['quote'])
    def candles(self,symbol,timeframe,count=220): return copy.deepcopy(self.data[symbol]['candles'][timeframe][-count:])
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
        raw_spread=os.environ.get('MT5_MAX_SPREAD','{}')
        try: self.max_spread=json.loads(raw_spread)
        except json.JSONDecodeError: raise DataError('MT5_MAX_SPREAD must be JSON')
        if not isinstance(self.max_spread,dict): raise DataError('invalid MT5_MAX_SPREAD')
        self.mt5=mt5; self.lock=threading.RLock(); self.mappings=mappings
        self.connected=False
    def _call(self, name, *args):
        try: return getattr(self.mt5,name)(*args)
        except Exception as exc:
            self.connected=False
            raise DataError(f'MT5 {name} failed') from exc
    def connect(self):
        with self.lock:
            if self.connected and hasattr(self.mt5, 'terminal_info'):
                terminal = self._call('terminal_info')
                if terminal is None or not getattr(terminal, 'connected', False):
                    try: self._call('shutdown')
                    except DataError: pass
                    self.connected = False
            if not self.connected:
                if not self._call('initialize'): raise DataError(f"MT5 initialize failed: {self._call('last_error')}")
                self.connected=True
    def health(self):
        with self.lock:
            self.connect()
            terminal = self._call('terminal_info') if hasattr(self.mt5, 'terminal_info') else None
            if terminal is None or not getattr(terminal, 'connected', False):
                raise DataError('MT5 terminal disconnected')
            return {'connected':True,'trade_allowed':bool(getattr(terminal,'trade_allowed',False))}
    def close(self):
        with self.lock:
            if self.connected:
                try: self._call('shutdown')
                finally: self.connected=False
    def _symbol(self, symbol):
        if symbol not in SYMBOLS: raise DataError('unsupported symbol')
        self.connect()
        actual=self.mappings.get(symbol,symbol)
        info=self._call('symbol_info',actual)
        if info is None or not actual or not isinstance(actual,str):
            raise DataError('broker symbol mapping unverified')
        # An alias is trusted only when explicitly configured and resolves to an exact MT5 name.
        if actual != symbol and self.mappings.get(symbol) != actual:
            raise DataError('broker symbol mapping unverified')
        if symbol not in actual.upper():
            raise DataError('broker symbol does not match canonical instrument')
        base,profit=getattr(info,'currency_base',None),getattr(info,'currency_profit',None)
        if base and profit and (base.upper()!=symbol[:3] or profit.upper()!=symbol[3:]):
            raise DataError('broker instrument currencies mismatch')
        if not self._call('symbol_select',actual,True): raise DataError('symbol_select failed')
        return actual,info
    def metadata(self,symbol):
        with self.lock:
            actual,i=self._symbol(symbol)
            account=self._call('account_info')
            if account is None: raise DataError('MT5 account unavailable')
            required=('trade_contract_size','trade_tick_size','trade_tick_value','point','volume_min','volume_max','volume_step','trade_stops_level')
            if any(not hasattr(i,key) for key in required): raise DataError('incomplete broker metadata')
            if any(finite(getattr(i,key),key) <= 0 for key in required[:-1]): raise DataError('invalid broker metadata')
            mode=getattr(i,'trade_mode',None)
            allowed={1:['BUY'],2:['SELL'],4:['BUY','SELL']}.get(mode,[])
            return {'symbol':symbol,'broker_symbol':actual,'asset_type':'metal' if symbol=='XAUUSD' else 'forex',
                    'source':'mt5','digits':getattr(i,'digits',None),
                    'market_type':'unverified','contract_type':'unverified','price_kind':'bid',
                    'trade_calc_mode':getattr(i,'trade_calc_mode',None),
                    'trade_mode':mode,'allowed_directions':allowed,
                    'base_currency':getattr(i,'currency_base',None),
                    'profit_currency':getattr(i,'currency_profit',None),
                    'margin_currency':getattr(i,'currency_margin',None),
                    'freeze_level':getattr(i,'trade_freeze_level',None),
                    'tick_value_profit':getattr(i,'trade_tick_value_profit',None),
                    'tick_value_loss':getattr(i,'trade_tick_value_loss',None),
                    'broker_server':getattr(account,'server',None),
                    'max_spread':self.max_spread.get(symbol),
                    'contract_size':i.trade_contract_size,
                    'tick_size':i.trade_tick_size,'tick_value':i.trade_tick_value,
                    'point':i.point,'volume_min':i.volume_min,'volume_max':i.volume_max,
                    'volume_step':i.volume_step,'stops_level':i.trade_stops_level,
                    'trade_allowed':bool(allowed) and getattr(account,'trade_allowed',False) is True,
                    'broker_hours':self.hours.get(symbol),
                    'account_currency':getattr(account,'currency',None),
                    'tick_value_currency':getattr(account,'currency',None) if account else None}
    def quote(self,symbol):
        with self.lock:
            actual,_=self._symbol(symbol); t=self._call('symbol_info_tick',actual)
            if t is None: raise DataError('tick unavailable')
            stamp=t.time_msc/1000 if getattr(t,'time_msc',0) else t.time
            bid,ask=finite(t.bid,'bid'),finite(t.ask,'ask')
            age=datetime.now(timezone.utc).timestamp()-finite(stamp,'tick time')
            if age>120 or age < -5: raise DataError('stale tick')
            if bid<=0 or ask<=bid: raise DataError('invalid bid/ask')
            return {'symbol':symbol,'bid':bid,'ask':ask,'spread':ask-bid,'time':stamp,
                    'provider':'mt5','freshness':'FRESH'}
    def candles(self,symbol,timeframe,count=220):
        if timeframe not in TIMEFRAMES: raise DataError('invalid timeframe')
        if not 1<=count<=10000: raise DataError('invalid candle count')
        with self.lock:
            actual,_=self._symbol(symbol)
            tf=getattr(self.mt5,'TIMEFRAME_'+timeframe)
            rows=self._call('copy_rates_from_pos',actual,tf,0,count+1)
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
        if side not in ('BUY','SELL') or min(finite(lots,'lots'),finite(entry,'entry'),finite(stop,'stop'))<=0:
            raise DataError('invalid broker profit calculation inputs')
        with self.lock:
            actual,_=self._symbol(symbol)
            typ=self.mt5.ORDER_TYPE_BUY if side=='BUY' else self.mt5.ORDER_TYPE_SELL
            result=self._call('order_calc_profit',typ,actual,lots,entry,stop)
            if result is None: raise DataError('order_calc_profit failed')
            return result
