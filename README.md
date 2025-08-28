# Public Market Data API (Render / Python 3.11)

FastAPI + yfinance. TW/US tickers. Includes `render.yaml` to force Python 3.11.9.

## Quick Deploy on Render (Recommended)
1. Push this folder to GitHub.
2. On Render: **New → Blueprint** (not Web Service), select this repo (uses `render.yaml`).
3. Hit Deploy. Python 3.11.9 will be used.
4. Test: `GET /health`

If you prefer Web Service instead of Blueprint:
- Create **Web Service**, connect repo.
- Set **Build Command**:  
  `pip install --upgrade pip wheel setuptools && pip install -r requirements.txt`
- Set **Start Command**:  
  `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Make sure `runtime.txt` = `3.11.9`
- In **Manual Deploy**, choose **Clear build cache & deploy** if previous build used Python 3.13.

## Local Dev
```
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints
- `/api/public/ohlcv?symbol=2330.TW&start=2020-01-01&end=2025-08-01`
- `/api/public/dividends?symbol=VYM&start=2018-01-01`
- `/api/public/splits?symbol=AAPL&start=2010-01-01`
- `/api/public/info?symbol=0056.TW`
- `/api/public/universe?market=ETF_US`

## Troubleshooting
- If build logs show `cpython-313` for pandas, your service is still on Python 3.13.
  - Use **Blueprint** flow with `render.yaml`, or
  - Add `.python-version` and `runtime.txt`, then **Clear build cache & deploy**.
