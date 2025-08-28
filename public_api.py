"""
public_api.py
This module defines a set of public API endpoints to serve stock market
data via FastAPI. The endpoints rely on the ``yfinance`` package
to source open data for both Taiwanese and U.S. equities. All
responses are JSON and are suitable for integration into your own
applications.

Endpoints provided:

* ``/api/public/ohlcv`` – returns daily open–high–low–close–volume
  records (plus adjusted close) for a given symbol within a date
  range. Supports paging via ``offset`` and ``limit`` query
  parameters.
* ``/api/public/dividends`` – returns a list of dividend cash
  payments for a symbol between two dates.
* ``/api/public/splits`` – returns a list of split ratios for a
  symbol between two dates.
* ``/api/public/info`` – returns basic company information such as
  name, currency, exchange and sector.
* ``/api/public/universe`` – returns example lists of common
  symbols; useful as a starting point or for testing. You can
  customise the lists or replace the implementation entirely.

The endpoints cache results in memory (using ``cachetools.TTLCache``)
for 10 minutes to minimise network calls. If you require
persistent caching, consider using a Redis or filesystem-backed
cache instead.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Tuple
import pandas as pd
import yfinance as yf
from cachetools import TTLCache
from datetime import datetime

__all__ = [
    "router",
]

# Router with prefix and tag to group the public endpoints
router = APIRouter(prefix="/api/public", tags=["public-data"])

# In-memory cache: stores up to 256 items, each expiring after 600 seconds
cache: TTLCache = TTLCache(maxsize=256, ttl=600)


def _symbol_norm(symbol: str) -> str:
    """Normalise a symbol string.

    If a symbol is purely numeric (e.g. '2330') it is assumed to be a
    Taiwanese equity and '.TW' is appended. If it already has a
    suffix (.TW or .TWO), it is returned unchanged. Other values are
    treated as-is (e.g. U.S. tickers like 'AAPL').

    :param symbol: The raw symbol string from the client.
    :returns: A normalised symbol string for use with yfinance.
    """
    s = symbol.strip().upper()
    if s.endswith(".TW") or s.endswith(".TWO"):
        return s
    # If symbol begins with a digit, assume a Taiwanese stock
    if s[:1].isdigit():
        return f"{s}.TW"
    return s


class OHLCVResp(BaseModel):
    """Pydantic model for OHLCV API responses."""

    date: str
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: float


class DividendResp(BaseModel):
    """Pydantic model for dividend responses."""

    date: str
    cash: float


class SplitResp(BaseModel):
    """Pydantic model for split responses."""

    date: str
    ratio: float


class InfoResp(BaseModel):
    """Pydantic model for basic info responses."""

    symbol: str
    longName: Optional[str] = None
    currency: Optional[str] = None
    exchange: Optional[str] = None
    marketCap: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None


def _fetch_ohlcv(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Internal helper to fetch OHLCV data from yfinance.

    :param symbol: A normalised symbol string (with suffix if required)
    :param start: Start date (YYYY-MM-DD)
    :param end: End date (YYYY-MM-DD)
    :returns: A pandas DataFrame with date index and OHLCV columns.
    """
    df = yf.download(symbol, start=start, end=end, auto_adjust=False, progress=False)
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "adj_close", "volume"])
    df = df.rename(columns=str.lower).reset_index()
    df = df[["date", "open", "high", "low", "close", "adj close", "volume"]]
    df.columns = ["date", "open", "high", "low", "close", "adj_close", "volume"]
    return df


def _fetch_dividends(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Internal helper to fetch dividend data from yfinance."""
    tk = yf.Ticker(symbol)
    div = tk.dividends
    if div is None or div.empty:
        return pd.DataFrame(columns=["date", "cash"])
    df = div.reset_index()
    df.columns = ["date", "cash"]
    df = df[(df["date"] >= pd.to_datetime(start)) & (df["date"] <= pd.to_datetime(end))]
    return df


def _fetch_splits(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Internal helper to fetch split events from yfinance."""
    tk = yf.Ticker(symbol)
    sp = tk.splits
    if sp is None or sp.empty:
        return pd.DataFrame(columns=["date", "ratio"])
    df = sp.reset_index()
    df.columns = ["date", "ratio"]
    df = df[(df["date"] >= pd.to_datetime(start)) & (df["date"] <= pd.to_datetime(end))]
    return df


def _fetch_info(symbol: str) -> Dict[str, Optional[any]]:
    """Internal helper to fetch basic company info."""
    tk = yf.Ticker(symbol)
    info: Dict[str, Optional[any]] = tk.info or {}
    return info


@router.get("/ohlcv", response_model=List[OHLCVResp])
def get_ohlcv(
    symbol: str = Query(..., description="股票代號，如 2330.TW 或 AAPL"),
    start: str = Query("2018-01-01"),
    end: str = Query(datetime.utcnow().strftime("%Y-%m-%d")),
    limit: int = Query(5000, ge=1, le=20000),
    offset: int = Query(0, ge=0),
):
    """Return daily OHLCV records (with adjusted close) for a symbol.

    You can use ``limit`` and ``offset`` to page through results when
    the date range is large.
    """
    sym = _symbol_norm(symbol)
    key = ("ohlcv", sym, start, end)
    if key in cache:
        df = cache[key]
    else:
        df = _fetch_ohlcv(sym, start, end)
        cache[key] = df
    total = len(df)
    lo = min(offset, total)
    hi = min(offset + limit, total)
    view = df.iloc[lo:hi].copy()
    if not view.empty:
        view["date"] = view["date"].dt.strftime("%Y-%m-%d")
    return view.to_dict(orient="records")  # type: ignore


@router.get("/dividends", response_model=List[DividendResp])
def get_dividends(
    symbol: str = Query(..., description="股票代號，如 2330.TW 或 AAPL"),
    start: str = Query("2018-01-01"),
    end: str = Query(datetime.utcnow().strftime("%Y-%m-%d")),
):
    """Return historical cash dividends for the given symbol."""
    sym = _symbol_norm(symbol)
    key = ("div", sym, start, end)
    if key in cache:
        df = cache[key]
    else:
        df = _fetch_dividends(sym, start, end)
        cache[key] = df
    df = df.copy()
    if not df.empty:
        df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df.to_dict(orient="records")  # type: ignore


@router.get("/splits", response_model=List[SplitResp])
def get_splits(
    symbol: str = Query(...),
    start: str = Query("2010-01-01"),
    end: str = Query(datetime.utcnow().strftime("%Y-%m-%d")),
):
    """Return historical stock split ratios for the given symbol."""
    sym = _symbol_norm(symbol)
    key = ("split", sym, start, end)
    if key in cache:
        df = cache[key]
    else:
        df = _fetch_splits(sym, start, end)
        cache[key] = df
    df = df.copy()
    if not df.empty:
        df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df.to_dict(orient="records")  # type: ignore


@router.get("/info", response_model=InfoResp)
def get_info(symbol: str = Query(...)):
    """Return basic company information for the given symbol."""
    sym = _symbol_norm(symbol)
    key = ("info", sym)
    if key in cache:
        info = cache[key]
    else:
        info = _fetch_info(sym)
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


# Example universe lists; you can customise or replace these
COMMON: Dict[str, List[str]] = {
    "ETF_TW": ["0050.TW", "0056.TW", "00878.TW", "00919.TW"],
    "ETF_US": ["SPY", "VOO", "VTI", "VYM", "SCHD", "QQQ"],
}


@router.get("/universe")
def get_universe(market: str = Query("ETF_TW", description="市場類型，例如 ETF_TW 或 ETF_US")):
    """Return a list of commonly traded symbols for a given market.

    This function is merely an example; replace or extend it to
    reference your own symbol lists or data sources.
    """
    symbols = COMMON.get(market.upper(), [])
    return {"market": market, "symbols": symbols}