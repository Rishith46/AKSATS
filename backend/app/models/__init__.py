from app.models.base import Base
from app.models import access, candidates, jobs, system  # noqa: F401  (register tables)

__all__ = ["Base"]