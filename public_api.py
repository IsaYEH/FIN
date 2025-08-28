from __future__ import annotations
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd
import yfinance as yf
from cachetools import TTLCache
from datetime import datetime

router = APIRouter(prefix="/api/public", tags=["public-data"])
cache = TTLCache(maxsize=256, ttl=600)

def _symbol_norm(symbol: str) -> str:
    s = symbol.strip().upper()
    if s.endswith(".TW") or s.endswith(".TWO"):
        return s
    if s[:1].isdigit():
        return f"{s}.TW"
    return s

class OHLCVResp(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: float

class DividendResp(BaseModel):
    date: str
    cash: float

class SplitResp(BaseModel):
    date: str
    ratio: float

class InfoResp(BaseModel):
    symbol: str
    longName: Optional[str] = None
    currency: Optional[str] = None
    exchange: Optional[str] = None
    marketCap: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None

@router.get("/ohlcv", response_model=List[OHLCVResp])
def get_ohlcv(
    symbol: str = Query(..., description="e.g. 2330.TW / AAPL"),
    start: str = Query("2018-01-01"),
    end: str = Query(datetime.utcnow().strftime("%Y-%m-%d")),
    limit: int = Query(5000, ge=1, le=20000),
    offset: int = Query(0, ge=0),
):
    sym = _symbol_norm(symbol)
    key = ("ohlcv", sym, start, end)
    df = cache.get(key)
    if df is None:
        df = yf.download(sym, start=start, end=end, auto_adjust=False, progress=False)
        if df is None or df.empty:
            return []
        df = df.rename(columns=str.lower).reset_index()
        df = df[["date", "open", "high", "low", "close", "adj close", "volume"]]
        df.columns = ["date","open","high","low","close","adj_close","volume"]
        cache[key] = df

    total = len(df)
    lo = min(offset, total)
    hi = min(offset + limit, total)
    view = df.iloc[lo:hi].copy()
    view["date"] = view["date"].dt.strftime("%Y-%m-%d")
    return view.to_dict(orient="records")

@router.get("/dividends", response_model=List[DividendResp])
def get_dividends(
    symbol: str = Query(...),
    start: str = Query("2018-01-01"),
    end: str = Query(datetime.utcnow().strftime("%Y-%m-%d")),
):
    sym = _symbol_norm(symbol)
    key = ("div", sym, start, end)
    df = cache.get(key)
    if df is None:
        tk = yf.Ticker(sym)
        div = tk.dividends
        if div is None or div.empty:
            return []
        df = div.reset_index()
        df.columns = ["date","cash"]
        df = df[(df["date"] >= pd.to_datetime(start)) & (df["date"] <= pd.to_datetime(end))]
        cache[key] = df
    df = df.copy()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df.to_dict(orient="records")

@router.get("/splits", response_model=List[SplitResp])
def get_splits(
    symbol: str = Query(...),
    start: str = Query("2010-01-01"),
    end: str = Query(datetime.utcnow().strftime("%Y-%m-%d")),
):
    sym = _symbol_norm(symbol)
    key = ("split", sym, start, end)
    df = cache.get(key)
    if df is None:
        tk = yf.Ticker(sym)
        sp = tk.splits
        if sp is None or sp.empty:
            return []
        df = sp.reset_index()
        df.columns = ["date","ratio"]
        df = df[(df["date"] >= pd.to_datetime(start)) & (df["date"] <= pd.to_datetime(end))]
        cache[key] = df
    df = df.copy()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df.to_dict(orient="records")

@router.get("/info", response_model=InfoResp)
def get_info(symbol: str = Query(...)):
    sym = _symbol_norm(symbol)
    key = ("info", sym)
    info = cache.get(key)
    if info is None:
        tk = yf.Ticker(sym)
        info = tk.info or {}
        cache[key] = info
    return InfoResp(
        symbol=sym,
        longName=info.get("longName"),
        currency=info.get("currency"),
        exchange=info.get("exchange"),
        marketCap=info.get("marketCap"),
        sector=info.get("sector"),
        industry=info.get("industry"),
    )

COMMON = {
    "ETF_TW": ["0050.TW","0056.TW","00878.TW","00919.TW"],
    "ETF_US": ["SPY","VOO","VTI","VYM","SCHD","QQQ"]
}

@router.get("/universe")
def get_universe(market: str = Query("ETF_TW")):
    return {"market": market, "symbols": COMMON.get(market.upper(), [])}
