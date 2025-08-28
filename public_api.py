from __future__ import annotations
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from cachetools import TTLCache
from datetime import datetime, timezone
import time
import requests

router = APIRouter(prefix="/api/public", tags=["public-data"])
cache = TTLCache(maxsize=256, ttl=600)

def _symbol_norm(symbol: str) -> str:
    s = symbol.strip().upper()
    if s.endswith(".TW") or s.endswith(".TWO"):
        return s
    if s[:1].isdigit():
        return f"{s}.TW"
    return s

def _date_to_unix(d: str) -> int:
    dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

def _yahoo_chart(sym: str, start: str, end: str, interval: str = "1d", include_events=True):
    p1 = _date_to_unix(start)
    # Yahoo的period2為「非包含」時刻，往後+86400保證包含end當日
    p2 = _date_to_unix(end) + 86400
    events = "div,splits" if include_events else "none"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval={interval}&events={events}"
    r = requests.get(url, timeout=20)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Yahoo chart error: {r.status_code}")
    data = r.json()
    return data

class OHLCVResp(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    adj_close: Optional[float] = None
    volume: Optional[float] = None

@router.get("/ohlcv", response_model=List[OHLCVResp])
def get_ohlcv(
    symbol: str = Query(...),
    start: str = Query("2018-01-01"),
    end: str = Query(datetime.utcnow().strftime("%Y-%m-%d")),
    limit: int = Query(5000, ge=1, le=20000),
    offset: int = Query(0, ge=0),
):
    sym = _symbol_norm(symbol)
    key = ("ohlcv_np", sym, start, end)
    rows = cache.get(key)
    if rows is None:
        data = _yahoo_chart(sym, start, end, "1d", include_events=False)
        res = data.get("chart", {}).get("result", [])
        if not res:
            return []
        r0 = res[0]
        ts = r0.get("timestamp", []) or []
        ind = r0.get("indicators", {})
        quote = (ind.get("quote") or [{}])[0]
        adj = (ind.get("adjclose") or [{}])[0]
        opens = quote.get("open", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        closes = quote.get("close", [])
        vols = quote.get("volume", [])
        adjs = adj.get("adjclose", [])

        rows = []
        for i, t in enumerate(ts):
            d = datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")
            rows.append({
                "date": d,
                "open": None if opens is None or i>=len(opens) else opens[i],
                "high": None if highs is None or i>=len(highs) else highs[i],
                "low":  None if lows  is None or i>=len(lows)  else lows[i],
                "close":None if closes is None or i>=len(closes) else closes[i],
                "adj_close": None if adjs is None or i>=len(adjs) else adjs[i],
                "volume": None if vols is None or i>=len(vols) else vols[i],
            })
        cache[key] = rows

    total = len(rows)
    lo = min(offset, total)
    hi = min(offset + limit, total)
    return rows[lo:hi]

class DividendResp(BaseModel):
    date: str
    cash: float

@router.get("/dividends", response_model=List[DividendResp])
def get_dividends(
    symbol: str = Query(...),
    start: str = Query("2018-01-01"),
    end: str = Query(datetime.utcnow().strftime("%Y-%m-%d")),
):
    sym = _symbol_norm(symbol)
    key = ("div_np", sym, start, end)
    rows = cache.get(key)
    if rows is None:
        data = _yahoo_chart(sym, start, end, "1d", include_events=True)
        res = data.get("chart", {}).get("result", [])
        if not res:
            return []
        events = res[0].get("events", {})
        divs = events.get("dividends", {})
        rows = []
        for _, v in sorted(divs.items(), key=lambda kv: int(kv[1]["date"])):
            dt = datetime.utcfromtimestamp(v["date"]).strftime("%Y-%m-%d")
            rows.append({"date": dt, "cash": float(v.get("amount", 0))})
        cache[key] = rows
    return rows

class SplitResp(BaseModel):
    date: str
    ratio: float

@router.get("/splits", response_model=List[SplitResp])
def get_splits(
    symbol: str = Query(...),
    start: str = Query("2010-01-01"),
    end: str = Query(datetime.utcnow().strftime("%Y-%m-%d")),
):
    sym = _symbol_norm(symbol)
    key = ("split_np", sym, start, end)
    rows = cache.get(key)
    if rows is None:
        data = _yahoo_chart(sym, start, end, "1d", include_events=True)
        res = data.get("chart", {}).get("result", [])
        if not res:
            return []
        events = res[0].get("events", {})
        splits = events.get("splits", {})
        rows = []
        for _, v in sorted(splits.items(), key=lambda kv: int(kv[1]["date"])):
            dt = datetime.utcfromtimestamp(v["date"]).strftime("%Y-%m-%d")
            # Yahoo給 "splitRatio": "4/1" 形式
            ratio_str = v.get("splitRatio", "1/1")
            try:
                a, b = ratio_str.split("/")
                ratio = float(a) / float(b)
            except Exception:
                ratio = 1.0
            rows.append({"date": dt, "ratio": ratio})
        cache[key] = rows
    return rows

class InfoResp(BaseModel):
    symbol: str
    longName: str | None = None
    currency: str | None = None
    exchange: str | None = None
    marketCap: float | None = None
    sector: str | None = None
    industry: str | None = None

@router.get("/info", response_model=InfoResp)
def get_info(symbol: str = Query(...)):
    # 以 Yahoo quoteSummary 取簡要資訊
    sym = _symbol_norm(symbol)
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{sym}?modules=price,assetProfile"
    r = requests.get(url, timeout=20)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Yahoo info error: {r.status_code}")
    js = r.json()
    result = (js.get("quoteSummary", {}) or {}).get("result", []) or []
    price = (result[0].get("price") if result else {}) or {}
    profile = (result[0].get("assetProfile") if result else {}) or {}

    return InfoResp(
        symbol=sym,
        longName=(price.get("longName") or price.get("shortName")),
        currency=price.get("currency"),
        exchange=price.get("exchangeName"),
        marketCap=(price.get("marketCap") or {}).get("raw"),
        sector=profile.get("sector"),
        industry=profile.get("industry"),
    )

COMMON = {
    "ETF_TW": ["0050.TW","0056.TW","00878.TW","00919.TW"],
    "ETF_US": ["SPY","VOO","VTI","VYM","SCHD","QQQ"]
}

@router.get("/universe")
def get_universe(market: str = Query("ETF_TW")):
    return {"market": market, "symbols": COMMON.get(market.upper(), [])}
