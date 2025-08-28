# Public Market Data API (No Pandas / No yfinance)

This version avoids pandas & yfinance by calling Yahoo's public chart/quoteSummary endpoints directly.
- ✅ Works on Python 3.11 and 3.13 (no native compilation)
- Endpoints: `/api/public/ohlcv`, `/dividends`, `/splits`, `/info`, `/universe`

## Deploy on Render
- Recommended: **Blueprint** → points to `render.yaml`
- Or create **Web Service** and use:
  - Build: `pip install --upgrade pip wheel setuptools && pip install -r requirements.txt`
  - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
  - (runtime.txt is still set to 3.11.9, but this build works on 3.13 too.)

## Local
```
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
