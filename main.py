from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from public_api import router as public_router

app = FastAPI(title="Public Market Data API (no-pandas)", version="0.1.0")

@app.get("/")
def index():
    return {
        "message": "Public Market Data API is running.",
        "try": [
            "/health",
            "/docs",
            "/api/public/ohlcv?symbol=2330.TW&start=2020-01-01&end=2025-08-01",
            "/api/public/dividends?symbol=VYM&start=2018-01-01",
            "/api/public/splits?symbol=AAPL&start=2010-01-01",
            "/api/public/info?symbol=0056.TW",
            "/api/public/universe?market=ETF_US"
        ]
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

app.include_router(public_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
