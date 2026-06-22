"""Nozzle Dashboard — serves the HTML interface."""

from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

TEMPLATE_DIR = Path(__file__).parent / "templates"


@router.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard HTML."""
    dashboard_path = TEMPLATE_DIR / "dashboard.html"
    if dashboard_path.exists():
        return dashboard_path.read_text(encoding="utf-8")
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)
