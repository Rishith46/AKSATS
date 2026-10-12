from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.access import User
from app.security import decode_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    with SessionLocal() as db:
        yield db


def get_current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    uid = decode_token(token)
    user = db.get(User, uid) if uid else None
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or expired credentials")
    return user


def user_permissions(user: User) -> set[str]:
    return {p.code for r in user.roles for p in r.permissions}


def require_permission(code: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if code not in user_permissions(user):
            raise HTTPException(status_code=403, detail="Permission denied")
        return user
    return checker