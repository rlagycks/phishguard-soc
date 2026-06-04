"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.routers import webhook, dashboard, admin

settings = get_settings()
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    # Schedule Gmail watch renewal every 23 hours (watch expires in 7 days but renew daily is safe)
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from app.database import SessionLocal
    from app.services import gmail_client
    from app.models import orm

    scheduler = AsyncIOScheduler()

    def renew_watch():
        db = SessionLocal()
        try:
            gmail_client.stop_watch()
        except Exception:
            pass
        try:
            resp = gmail_client.setup_watch()
            watch = db.query(orm.WatchStatus).first()
            if watch:
                watch.expiration_ms = int(resp.get("expiration", 0))
                db.commit()
        except Exception as e:
            logging.getLogger(__name__).warning("Watch renewal failed: %s", e)
        finally:
            db.close()

    scheduler.add_job(renew_watch, "interval", hours=23, id="renew_watch")
    scheduler.start()

    yield

    scheduler.shutdown()


app = FastAPI(
    title="Phishing SOC API",
    description="Gmail Webhook 기반 피싱 메일 자동 분석·격리 시스템",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router)
app.include_router(dashboard.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# React SPA static serving for single-process deployment. During local frontend
# development Vite serves the app, but production can build frontend/dist and let
# FastAPI serve the compiled files from the same origin.
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if (_FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="frontend-assets")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str):
    index = _FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Frontend build not found. Run npm run build in ../frontend.")
