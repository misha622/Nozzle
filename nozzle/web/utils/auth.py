"""API key authentication middleware."""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from nozzle.settings import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Verify the API key from header."""
    if not settings.api_key:
        return "anonymous"

    if api_key is None:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Missing X-API-Key header",
        )

    if api_key != settings.api_key:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key
