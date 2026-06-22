# Nozzle

ML-powered alert deduplication for SIEM systems.

## What it does

Nozzle connects to your SIEM (Wazuh, Elastic, etc.), ingests alerts, and automatically groups them into meaningful clusters — reducing alert noise by up to 90% without missing real incidents.

### Current Features
- Wazuh adapter with JWT auth and pagination
- Rule-based clustering (rule_id + agent_name + time window)
- FastAPI REST API
- SQLite storage with Alembic migrations
- Extensible plugin architecture for sources and clustering strategies

### Quick Start

```bash
# Clone
git clone https://github.com/misha622/Nozzle.git
cd Nozzle

# Setup
python -m venv .venv
.venv\Scripts\activate
pip install -e .

# Run migrations
alembic upgrade head

# Start server
python -m uvicorn nozzle.main:app --reload --host 0.0.0.0 --port 8000

# Open in browser
# http://localhost:8000/api/v1/health
API Endpoints
MethodPathDescription
GET/api/v1/healthHealth check
GET/api/v1/health/readyReadiness check (DB)
GET/api/v1/alerts/List alerts
POST/api/v1/alerts/ingest/{source_id}Ingest alerts from source
GET/api/v1/clusters/List clusters
POST/api/v1/clusters/runRun clustering
GET/api/v1/sources/List sources
POST/api/v1/sources/Create source
Architecture
text
Sources (Wazuh/Elastic/...) → Adapter → Normalizer → DB
                                                    ↓
Alerts ← Clustering Manager ← Strategies (rule_based/ML/...)
   ↓
Clusters → API → Dashboard (Streamlit)
License
AGPL-3.0
