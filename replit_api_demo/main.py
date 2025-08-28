"""
main.py
Entry point for the public data API service. This script sets up
a FastAPI application, adds CORS middleware for cross-origin
requests, and includes the router from ``public_api.py``. To run
this service locally, execute:

    uvicorn main:app --host 0.0.0.0 --port 8000

Alternatively, use Docker or Docker Compose with a corresponding
``Dockerfile``. The service exposes endpoints under
``/api/public`` for open stock market data.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .public_api import router as public_router


app = FastAPI(title="Public Market Data API", version="1.0.0")

# Allow all origins, methods, and headers. For production, restrict
# this configuration to trusted clients.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Simple health endpoint returning a static response."""
    return {"ok": True}


# Include the public data router under the /api/public prefix
app.include_router(public_router)