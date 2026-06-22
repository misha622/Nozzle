from fastapi import APIRouter

router = APIRouter()


@router.get("/dashboard")
async def dashboard():
    return {
        "total_alerts_24h": 0,
        "total_clusters_24h": 0,
        "alerts_saved_pct": 0.0,
        "top_noisy_rules": [],
        "false_positive_rate": 0.0,
        "avg_cluster_confidence": 0.0,
        "incidents_missed": 0,
    }