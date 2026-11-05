"""Local read-only REST facade. Set a provider in app.state.provider before use."""
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Literal
from .core import SYMBOLS, TIMEFRAMES, DataError, analyze, size_lots, backtest
from .providers import MT5Provider
from .sessions import session_snapshot
from .scanner import scan
from .strategies import STRATEGIES

app=FastAPI(title='Trade AI Forex',version='0.2.0')
app.state.provider=None
app.state.news_items=None
app.state.calendar_events=None
app.state.analytical_extension=None
app.state.information_provider=None

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
    strategies: list[dict] | None = None
    session: dict | None = None
    confirmations: list[dict] | None = None
    market_structure: dict | None = None

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
    price_basis: Literal['bid','mid']='bid'
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
def analysis(symbol:Literal['XAUUSD','EURUSD','GBPUSD','USDJPY'],timeframe:Literal['M5','M15','M30','H1','H4','D1']='M15', confirmations:str|None=None):
    confirm=tuple(x.strip().upper() for x in confirmations.split(',')) if confirmations else None
    result=call(lambda: analyze(provider(),symbol,timeframe,confirmation_timeframes=confirm))
    if result['data_status']!='OK': return JSONResponse(status_code=503,content=result)
    return result

@app.get('/api/v1/signals/{symbol}', response_model=AnalysisResponse)
def signals(symbol:Literal['XAUUSD','EURUSD','GBPUSD','USDJPY'],timeframe:Literal['M5','M15','M30','H1','H4','D1']='M15',confirmations:str|None=None): return analysis(symbol,timeframe,confirmations)

@app.post('/api/v1/risk/calculate', response_model=RiskResponse)
def calculate(req:RiskRequest):
    return call(lambda: size_lots(req.balance,req.risk_pct,req.entry,req.stop_loss,provider().metadata(req.symbol),
                (lambda side,lots,e,s: provider().loss_for(req.symbol,side,lots,e,s)) if hasattr(provider(),'loss_for') else None,
                req.direction,req.account_currency))

@app.get('/api/v1/news')
def news():
    items=app.state.news_items
    return {'items':items or [],'provider':'configured-feed' if items is not None else None,
            'data_status':'OK' if items is not None else 'DATA_UNAVAILABLE',
            'reason':None if items is not None else 'Forex news source not configured'}

@app.get('/api/v1/calendar')
def calendar(symbol:Literal['XAUUSD','EURUSD','GBPUSD','USDJPY']|None=None):
    from .information import filter_events
    events=app.state.calendar_events
    return {'events':filter_events(events,symbol) if events is not None else [],
            'provider':'configured-calendar' if events is not None else None,
            'data_status':'OK' if events is not None else 'DATA_UNAVAILABLE',
            'reason':None if events is not None else 'Economic calendar source not configured'}

@app.post('/api/v1/backtests', response_model=BacktestResponse)
def backtests(req:BacktestRequest):
    return call(lambda: {'result':backtest(provider().candles(req.symbol,req.timeframe,req.count),req.direction,
                req.entry,req.stop_loss,req.take_profit,req.spread,req.price_basis),'provider':provider().name,'data_status':'OK'})

@app.get('/api/v1/sessions/{symbol}')
def sessions(symbol:Literal['XAUUSD','EURUSD','GBPUSD','USDJPY']):
    p=provider()
    m=call(lambda:p.metadata(symbol))
    return session_snapshot(datetime.now(timezone.utc),symbol,m.get('trade_allowed'),m.get('broker_hours'))

@app.get('/api/v1/strategies')
def strategies():
    return {'strategies':STRATEGIES,'version':'v1','provider':None}

@app.get('/api/v1/scanner')
def scanner_route(symbols:str='XAUUSD',timeframes:str='M15'):
    syms=tuple(x.strip().upper() for x in symbols.split(',') if x.strip())
    tfs=tuple(x.strip().upper() for x in timeframes.split(',') if x.strip())
    if not syms or not tfs or len(syms)*len(tfs)>24 or any(x not in SYMBOLS for x in syms) or any(x not in TIMEFRAMES for x in tfs):
        raise HTTPException(422,{'status':'ERROR','reason':'invalid scanner symbols/timeframes or pair limit'})
    return scan(provider(),syms,tfs)

class StrategyBacktestRequest(BaseModel):
    price_basis: Literal['bid','mid']='bid'
    symbol: Literal['XAUUSD','EURUSD','GBPUSD','USDJPY']
    timeframe: Literal['M5','M15','M30','H1','H4','D1']='M15'
    count: int=Field(ge=220,le=2000)
    spread: float=Field(ge=0)
    commission: float=Field(ge=0,default=0)
    slippage: float=Field(ge=0,default=0)
    holdout: float=Field(gt=0,lt=.5,default=.25)
    seed: int=19

@app.post('/api/v1/strategy-backtests')
def strategy_backtests(req:StrategyBacktestRequest):
    from .research import strategy_backtest
    p=provider()
    result=call(lambda: strategy_backtest(p.candles(req.symbol,req.timeframe,req.count),
                        req.spread,req.commission,req.slippage,req.holdout,req.seed,req.price_basis))
    return {'result':result,'provider':p.name,'data_status':'OK'}

class RiskPolicyRequest(BaseModel):
    symbol: Literal['XAUUSD','EURUSD','GBPUSD','USDJPY']
    direction: Literal['BUY','SELL']
    timeframe: Literal['M5','M15','M30','H1','H4','D1']='M15'
    entry: float=Field(gt=0)
    stop_loss: float=Field(gt=0)
    take_profit_1: float=Field(gt=0)
    balance: float=Field(gt=0)
    risk_pct: float=Field(gt=0,le=5)
    max_spread: float=Field(gt=0)
    records: list[dict]=Field(default_factory=list,max_length=100)

@app.post('/api/v1/risk/policy')
def policy_route(req:RiskPolicyRequest):
    from .policy import assess
    p=provider();meta=call(lambda:p.metadata(req.symbol));q=call(lambda:p.quote(req.symbol))
    meta={**meta,'spread':q['ask']-q['bid']}
    plan=req.model_dump(include={'symbol','direction','timeframe','entry','stop_loss','take_profit_1'})
    return call(lambda:assess(plan,meta,req.balance,req.risk_pct,req.records,
        max_spread=req.max_spread,calc_profit=(lambda side,lots,e,s:p.loss_for(req.symbol,side,lots,e,s))
        if hasattr(p,'loss_for') else None,account_currency=meta.get('account_currency')))

@app.get('/api/v1/alerts/{symbol}')
def alerts_route(symbol:Literal['XAUUSD','EURUSD','GBPUSD','USDJPY'],timeframe:Literal['M5','M15','M30','H1','H4','D1']='M15'):
    from .alerts import AlertEngine
    if not hasattr(app.state,'alert_engine'): app.state.alert_engine=AlertEngine()
    result=analyze(provider(),symbol,timeframe)
    return {'events':app.state.alert_engine.evaluate(result),'data_status':result['data_status'],
            'provider':provider().name}

class WalkForwardRequest(StrategyBacktestRequest):
    count: int=Field(ge=260,le=2000)
    folds: int=Field(ge=2,le=5,default=3)

@app.post('/api/v1/walk-forward')
def walk_forward_route(req:WalkForwardRequest):
    from .research import walk_forward
    p=provider()
    result=call(lambda:walk_forward(p.candles(req.symbol,req.timeframe,req.count),
        req.spread,folds=req.folds,commission=req.commission,slippage=req.slippage,
        holdout=req.holdout,seed=req.seed,price_basis=req.price_basis))
    return {'result':result,'provider':p.name,'data_status':'OK'}


# Additive V5 contract; existing V1 routes and response meanings are retained.
from .unified import UnifiedAnalysis, unified_analyze


class UnifiedRequest(BaseModel):
    model_config = {'extra': 'forbid', 'allow_inf_nan': False}
    symbol: Literal['XAUUSD','EURUSD','GBPUSD','USDJPY']
    timeframe: Literal['M5','M15','M30','H1','H4','D1']='M15'
    confirmations: list[Literal['M5','M15','M30','H1','H4','D1']] = Field(default_factory=lambda: ['H4'], min_length=1, max_length=3)
    require_private: bool = False
    balance: float | None = Field(default=None, gt=0)
    risk_pct: float = Field(default=1, gt=0, le=5)
    commission_per_lot: float = Field(default=0, ge=0)
    slippage_price: float = Field(default=0, ge=0)
    records: list[dict] = Field(default_factory=list, max_length=100)


@app.post('/api/v5/analysis', response_model=UnifiedAnalysis)
def unified_analysis_route(req: UnifiedRequest):
    """Analytical POST has no persistent or broker execution side effects."""
    from .contracts import canonical
    if len(canonical(req.records)) > 100_000:
        raise HTTPException(422, {'status':'ERROR','reason':'manual records exceed budget'})
    return unified_analyze(provider(), req.symbol, req.timeframe,
                           confirmations=tuple(req.confirmations),
                           extension=app.state.analytical_extension,
                           require_private=req.require_private, balance=req.balance,
                           risk_pct=req.risk_pct, records=req.records,
                           commission_per_lot=req.commission_per_lot, slippage_price=req.slippage_price,
                           information_provider=app.state.information_provider)


@app.get('/api/v5/information')
def unified_information_route():
    from .macro import information_context
    return information_context(app.state.information_provider)
