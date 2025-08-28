from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from public_api import router as public_router

app = FastAPI(title="Public Market Data API", version="0.3.0")

# CORS：私用可開放 *；若要限制，改成你的前端網域白名單
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

# 掛上公開資料路由
app.include_router(public_router)

# 本機開發用：Render 不會走到這段
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
