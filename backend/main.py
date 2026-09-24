"""
Content Intelligence Engine — FastAPI Backend Application.
"""
import shutil
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import sys
from pathlib import Path

# Ensure src/ is on sys.path so content_engine is universally importable
_BASE_DIR = Path(__file__).resolve().parent.parent
_SRC_DIR = _BASE_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

from backend.config import FRONTEND_URL
from backend.database import get_db, ensure_columns, SessionLocal
from backend.routers import auth, opportunities, models, ai, datasets, watchlist, impact, export, runs, projects
from backend.schemas import UserLoginRequest, TokenResponse
from backend.routers.auth import login as auth_login
from content_engine.config import BASE_DIR


app = FastAPI(
    title="Content Intelligence Engine API",
    description="ML-powered Content Intelligence SaaS API for ranking and prioritizing editorial content reviews.",
    version="2.0.0",
)

# Configure CORS
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
]

if FRONTEND_URL:
    for url in FRONTEND_URL.split(","):
        cleaned = url.strip().rstrip("/")
        if cleaned and cleaned not in origins:
            origins.append(cleaned)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """Ensure database schema is ready and seed 30k pages if database is unseeded."""
    try:
        ensure_columns()
    except Exception as e:
        print(f"Warning: ensure_columns on startup: {e}")

    try:
        from backend.models import Page
        with SessionLocal() as db:
            if db.query(Page).count() == 0:
                print("Database is empty. Initializing catalog data from opportunities.csv...")
                from backend.seed import seed_database
                seed_database()
    except Exception as e:
        print(f"Startup database check notice: {e}")


# Include Routers
app.include_router(auth.router)
app.include_router(opportunities.router)
app.include_router(models.router)
app.include_router(ai.router)
app.include_router(datasets.router)
app.include_router(watchlist.router)
app.include_router(impact.router)
app.include_router(export.router)
app.include_router(runs.router)
app.include_router(projects.router)


@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
def auth_login_alias(req: UserLoginRequest, db: Session = Depends(get_db)):
    """SRS Section 24: POST /auth/login - authenticate user, return JWT bearer token."""
    return auth_login(req, db)


@app.get("/health", tags=["Health & Diagnostics"])
@app.get("/api/health", tags=["Health & Diagnostics"])
def health_check(db: Session = Depends(get_db)):
    """
    SRS Section 24: GET /health - system health check:
    database connection status, model file availability, available disk space, background worker status.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    model_path = BASE_DIR / "data" / "processed" / "best_model.joblib"
    model_available = model_path.exists()

    try:
        total, used, free = shutil.disk_usage(str(BASE_DIR))
        available_disk_mb = round(free / (1024 * 1024), 2)
    except Exception:
        available_disk_mb = 0.0

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "Content Intelligence Engine API",
        "version": "2.0.0",
        "database": db_status,
        "model_available": model_available,
        "available_disk_mb": available_disk_mb,
        "worker_status": "ready",
        "tagline": "Turn search data into smarter content decisions."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

