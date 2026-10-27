from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, user_permissions
from app.models.access import User
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username.strip().lower()))
    if not user or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "designation": user.designation,
        "roles": [r.name for r in user.roles],
        "permissions": sorted(user_permissions(user)),
    }