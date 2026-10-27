from fastapi import APIRouter, Depends

from app.deps import require_permission
from app.models.access import User
from app.visa import VISA_OPTIONS

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/visa-statuses")
def visa_statuses(user: User = Depends(require_permission("candidate.view"))):
    return [{"value": v, "label": label} for v, label in VISA_OPTIONS]