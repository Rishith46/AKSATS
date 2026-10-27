import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db import engine
from app.routers import auth, candidate_delete, candidates, documents, inbox, notes, parsing, profile, jobs, matching, jd, meta, candidate_edit
from app.services import worker

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("aks_ats")


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker.start()
    yield
    worker.stop()


app = FastAPI(title="ALL KNOWN SERVICES ATS", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(candidates.router)
app.include_router(candidate_delete.router)
app.include_router(notes.router)
app.include_router(documents.router)
app.include_router(parsing.router)
app.include_router(inbox.router)
app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(matching.router)
app.include_router(jd.router)
app.include_router(meta.router)
app.include_router(candidate_edit.router)


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            vec = conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname='vector'")
            ).scalar()
    except Exception as exc:
        log.exception("Health check failed")
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok", "database": "up", "pgvector": vec}