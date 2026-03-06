"""الإعدادات"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.database import get_db
from core.security import get_current_user, require_roles
from models.models import Setting, User, UserRole

router = APIRouter()

class SettingUpdate(BaseModel):
    value: str

@router.get("/")
async def get_settings(db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    return {s.key: s.value for s in db.query(Setting).all()}

@router.put("/{key}")
async def update_setting(key: str, data: SettingUpdate, db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))):
    s = db.query(Setting).filter(Setting.key == key).first()
    if s:
        s.value = data.value
    else:
        db.add(Setting(key=key, value=data.value))
    db.commit()
    return {"key": key, "value": data.value}
