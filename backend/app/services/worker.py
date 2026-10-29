import logging
import threading
import time

from sqlalchemy import select, update

from app.config import settings
from app.db import SessionLocal
from app.models.system import ResumeIngestion
from app.services.gmail_inbox import is_configured, poll_gmail
from app.services.process_inbox import process_ingestion

log = logging.getLogger("aks_ats.worker")

_stop = threading.Event()
_thread: threading.Thread | None = None


def recover() -> None:
    """Rows left in 'Processing' were interrupted. Flag them for review, never re-run silently."""
    with SessionLocal() as db:
        res = db.execute(
            update(ResumeIngestion)
            .where(ResumeIngestion.status == "Processing")
            .values(status="Needs Review",
                    issues={"reason": "Interrupted by a restart; review or re-upload"}))
        db.commit()
        if res.rowcount:
            log.warning("Marked %s interrupted inbox rows as Needs Review", res.rowcount)


def _loop() -> None:
    log.info("Inbox worker started")
    next_gmail_poll = 0.0
    if not is_configured():
        log.info("Gmail resume polling is disabled; configure Gmail OAuth settings to enable it")
    while not _stop.is_set():
        try:
            now = time.monotonic()
            if is_configured() and now >= next_gmail_poll:
                try:
                    with SessionLocal() as db:
                        queued = poll_gmail(db)
                    if queued:
                        log.info("Queued %s resume attachment(s) from Gmail", queued)
                except Exception:
                    log.exception("Gmail inbox polling failed; it will retry")
                next_gmail_poll = time.monotonic() + max(30, settings.gmail_poll_seconds)
            with SessionLocal() as db:
                rid = db.scalar(select(ResumeIngestion.id)
                                .where(ResumeIngestion.status == "Received")
                                .order_by(ResumeIngestion.id).limit(1))
                if rid is None:
                    _stop.wait(3)
                    continue
                try:
                    process_ingestion(db, rid)
                except Exception:
                    db.rollback()
                    log.exception("Worker failed on inbox row %s", rid)
                    row = db.get(ResumeIngestion, rid)
                    if row and row.status in ("Received", "Processing"):
                        row.status = "Failed"
                        row.issues = {"reason": "Processing error; see server log"}
                        db.commit()
        except Exception:
            log.exception("Worker loop error")
            _stop.wait(5)
    log.info("Inbox worker stopped")


def start() -> None:
    global _thread
    recover()
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="inbox-worker", daemon=True)
    _thread.start()


def stop() -> None:
    _stop.set()
    if _thread:
        _thread.join(timeout=120)