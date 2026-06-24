from contextlib import asynccontextmanager
from fastapi import FastAPI, Security
from fastapi.middleware.cors import CORSMiddleware

from nozzle.settings import settings
from nozzle.core.logging_config import setup_logging
from nozzle.api.router import api_router
from nozzle.web.utils.auth import verify_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    setup_logging(debug=settings.debug)
    # TODO: init DB pool, start scheduler
    yield
    # TODO: close DB pool, stop scheduler


def create_app() -> FastAPI:
    import logging
    log = logging.getLogger(__name__)
    if not settings.api_key:
        log.warning("NOZZLE_API_KEY is empty — API is unprotected. Set NOZZLE_API_KEY in .env for production.")
    app = FastAPI(
        title="Nozzle",
        description="ML-powered alert deduplication for SIEM systems",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1", dependencies=[Security(verify_api_key)])

    return app


app = create_app()