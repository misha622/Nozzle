from fastapi import APIRouter
from nozzle.api.v1 import health, alerts, clusters, rules, stats, sources, users
from nozzle.web.app import router as web_router

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(clusters.router, prefix="/clusters", tags=["Clusters"])
api_router.include_router(rules.router, prefix="/rules", tags=["Rules"])
api_router.include_router(stats.router, prefix="/stats", tags=["Stats"])
api_router.include_router(sources.router, prefix="/sources", tags=["Sources"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# Web dashboard
api_router.include_router(web_router, prefix="/dashboard", tags=["Dashboard"])
