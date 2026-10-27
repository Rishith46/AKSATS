from sqlalchemy import select

from app.db import SessionLocal
from app.models.system import MatchConfig
from app.services.matching import DEFAULT_WEIGHTS

with SessionLocal() as db:
    cfg = db.scalar(select(MatchConfig).where(MatchConfig.name == "default"))
    if cfg is None:
        db.add(MatchConfig(name="default", weights=dict(DEFAULT_WEIGHTS), is_active=True))
        print("match weights created")
    else:
        cfg.weights = dict(DEFAULT_WEIGHTS)
        cfg.is_active = True
        print("match weights updated")
    db.commit()