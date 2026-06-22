from fastapi import APIRouter

router = APIRouter()


@router.get("/top-noisy")
async def top_noisy_rules():
    return {"items": []}