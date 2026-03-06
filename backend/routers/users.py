"""إدارة المستخدمين"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from core.database import get_db
from core.security import get_current_user, require_roles, get_password_hash
from models.models import User, UserRole

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    full_name: str
    password: str
    role: UserRole = UserRole.pharmacist

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

@router.get("/")
async def get_users(db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))):
    return [{"id": u.id, "username": u.username, "full_name": u.full_name,
             "role": u.role, "is_active": u.is_active, "last_login": u.last_login}
            for u in db.query(User).all()]

@router.post("/", status_code=201)
async def create_user(data: UserCreate, db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "اسم المستخدم موجود مسبقاً")
    u = User(username=data.username, full_name=data.full_name,
             hashed_password=get_password_hash(data.password), role=data.role)
    db.add(u); db.commit(); db.refresh(u)
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role}

@router.put("/{uid}")
async def update_user(uid: int, data: UserUpdate, db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))):
    u = db.query(User).filter(User.id == uid).first()
    if not u: raise HTTPException(404, "المستخدم غير موجود")
    if data.full_name: u.full_name = data.full_name
    if data.role: u.role = data.role
    if data.is_active is not None: u.is_active = data.is_active
    if data.password: u.hashed_password = get_password_hash(data.password)
    db.commit()
    return {"message": "تم التحديث"}

@router.delete("/{uid}")
async def delete_user(uid: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))):
    u = db.query(User).filter(User.id == uid).first()
    if not u: raise HTTPException(404, "غير موجود")
    if u.id == current_user.id: raise HTTPException(400, "لا يمكنك حذف نفسك")
    db.delete(u); db.commit(); return {"message": "تم الحذف"}
