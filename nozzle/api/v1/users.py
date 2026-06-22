from fastapi import APIRouter

router = APIRouter()


@router.get("/me")
async def get_current_user():
    return {"id": "00000000-0000-0000-0000-000000000000", "email": "admin@nozzle.local"}