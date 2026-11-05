"""Local read-only REST facade. Set a provider in app.state.provider before use."""
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Literal
from .core import SYMBOLS, TIMEFRAMES, DataError, analyze, size_lots, backtest
from .providers import MT5Provider

app=FastAPI(title='Trade AI Forex',version='0.2.0')
app.state.provider=None

def provider():
    if app.state.provider is None:
        try: app.state.provider=MT5Provider()
        except DataError as exc: raise HTTPException(503,{'status':'DATA_UNAVAILABLE','reason':str(exc)})
    return app.state.provider

def call(fn):
    try: return fn()
    except DataError as exc:
        reason=str(exc)
        status='STALE' if 'stale' in reason else 'DATA_UNAVAILABLE' if any(x in reason for x in ('unavailable','disconnected','failed','no candles')) else 'ERROR'
        raise HTTPException(503 if status!='ERROR' else 422,{'status':status,'reason':reason})
    except KeyError as exc: raise HTTPException(404,{'status':'DATA_UNAVAILABLE','reason':str(exc)})

class AnalysisResponse(BaseModel):
    symbol: str
    timeframe: str
    provider: str
    timestamp: str
    signal: Literal['BUY','SELL','WAIT']
    plan: dict | None
    reasons: list[str]
    data_status: str
    indicators: dict | None = None

class BacktestResponse(BaseModel):
    result: dict
    provider: str
    data_status: str

class RiskResponse(BaseModel):
    lots: float
    estimated_risk: float
    risk_cap: float
    currency: str

class RiskRequest(BaseModel):
    symbol: Literal['XAUUSD','EURUSD','GBPUSD','USDJPY']
    direction: Literal['BUY','SELL']
    balance: float=Field(gt=0)
    risk_pct: float=Field(gt=0,le=5)
    entry: float=Field(gt=0)
    stop_loss: float=Field(gt=0)
    account_currency: str

class BacktestRequest(BaseModel):
    symbol: Literal['XAUUSD','EURUSD','GBPUSD','USDJPY']
    timeframe: Literal['M5','M15','M30','H1','H4','D1']='M15'
    direction: Literal['BUY','SELL']
    entry: float=Field(gt=0)
    stop_loss: float=Field(gt=0)
    take_profit: float=Field(gt=0)
    spread: float=Field(ge=0)
    count: int=Field(ge=2,le=10000)

@app.get('/api/v1/health')
def health():
    p=provider()
    if hasattr(p,'health'):
        call(p.health)
    return {'status':'OK','provider':p.name,'data_status':'TEST_ONLY' if p.name=='fixture-test-only' else 'OK',
            'timestamp':datetime.now(timezone.utc).isoformat()}

@app.get('/api/v1/symbols')
def symbols(): return {'symbols':SYMBOLS,'provider':provider().name,'data_status':'OK'}

@app.get('/api/v1/symbols/{symbol}/metadata')
def metadata(symbol:Literal['XAUUSD','EURUSD','GBPUSD','USDJPY']): return call(lambda: {'data':provider().metadata(symbol),'provider':provider().name,'data_status':'OK'})

@app.get('/api/v1/quotes/{symbol}')
def quotes(symbol:Literal['XAUUSD','EURUSD','GBPUSD','USDJPY']): return call(lambda: {'data':provider().quote(symbol),'provider':provider().name,'data_status':'OK'})

@app.get('/api/v1/candles/{symbol}')
def candles(symbol:Literal['XAUUSD','EURUSD','GBPUSD','USDJPY'],timeframe:Literal['M5','M15','M30','H1','H4','D1']='M15',count:int=Query(220,ge=1,le=10000)):
    return call(lambda: {'data':provider().candles(symbol,timeframe,count),'provider':provider().name,'data_status':'OK'})

@app.get('/api/v1/analysis/{symbol}', response_model=AnalysisResponse)
def analysis(symbol:Literal['XAUUSD','EURUSD','GBPUSD','USDJPY'],timeframe:Literal['M5','M15','M30','H1','H4','D1']='M15'):
    result=call(lambda: analyze(provider(),symbol,timeframe))
    if result['data_status']!='OK': return JSONResponse(status_code=503,content=result)
    return result

@app.get('/api/v1/signals/{symbol}', response_model=AnalysisResponse)
def signals(symbol:Literal['XAUUSD','EURUSD','GBPUSD','USDJPY'],timeframe:Literal['M5','M15','M30','H1','H4','D1']='M15'): return analysis(symbol,timeframe)

@app.post('/api/v1/risk/calculate', response_model=RiskResponse)
def calculate(req:RiskRequest):
    return call(lambda: size_lots(req.balance,req.risk_pct,req.entry,req.stop_loss,provider().metadata(req.symbol),
                (lambda side,lots,e,s: provider().loss_for(req.symbol,side,lots,e,s)) if hasattr(provider(),'loss_for') else None,
                req.direction,req.account_currency))

@app.get('/api/v1/news')
def news(): return {'items':[],'provider':None,'data_status':'DATA_UNAVAILABLE','reason':'Forex news source not configured'}

@app.get('/api/v1/calendar')
def calendar(): return {'events':[],'provider':None,'data_status':'DATA_UNAVAILABLE','reason':'Economic calendar source not configured'}

@app.post('/api/v1/backtests', response_model=BacktestResponse)
def backtests(req:BacktestRequest):
    return call(lambda: {'result':backtest(provider().candles(req.symbol,req.timeframe,req.count),req.direction,
                req.entry,req.stop_loss,req.take_profit,req.spread),'provider':provider().name,'data_status':'OK'})
