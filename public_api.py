from fastapi import APIRouter

router = APIRouter(prefix="/api/public", tags=["public-data"])

@router.get("/ping")
def ping():
    return {"pong": True}
