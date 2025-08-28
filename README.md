# Public Market Data API (Render / Python)

A FastAPI service exposing public market data via yfinance.
- Endpoints: `/api/public/ohlcv`, `/dividends`, `/splits`, `/info`, `/universe`
- Works for TW/US tickers (e.g., `2330.TW`, `AAPL`)

## Deploy on Render
1. Push this repo to GitHub/GitLab/Bitbucket.
2. Create a **Web Service** on Render → Connect your repo.
3. **Build Command**:
   ```
   pip install --upgrade pip wheel setuptools && pip install -r requirements.txt
   ```
4. **Start Command**:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
5. Ensure `runtime.txt` = `3.11.9`.

## Local dev
```
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Examples
- OHLCV: `/api/public/ohlcv?symbol=2330.TW&start=2020-01-01&end=2025-08-01`
- Dividends: `/api/public/dividends?symbol=VYM&start=2018-01-01`
- Splits: `/api/public/splits?symbol=AAPL&start=2010-01-01`
- Info: `/api/public/info?symbol=0056.TW`
- Universe: `/api/public/universe?market=ETF_US`
