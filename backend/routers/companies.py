"""الشركات والموردون"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from pydantic import BaseModel
from core.database import get_db
from core.security import get_current_user, require_roles
from models.models import Company, User, UserRole

router = APIRouter()

class CompanyCreate(BaseModel):
    name: str
    type: str
    address: Optional[str] = None
    city: Optional[str] = None
    phone1: Optional[str] = None
    phone2: Optional[str] = None
    email: Optional[str] = None
    rep_name: Optional[str] = None
    rep_phone: Optional[str] = None
    payment_terms: str = "نقداً"
    notes: Optional[str] = None

def comp_dict(c):
    return {"id": c.id, "name": c.name, "type": c.type, "address": c.address,
            "city": c.city, "phone1": c.phone1, "phone2": c.phone2, "email": c.email,
            "rep_name": c.rep_name, "rep_phone": c.rep_phone,
            "payment_terms": c.payment_terms, "notes": c.notes, "is_active": c.is_active}

@router.get("/")
async def get_companies(search: Optional[str] = Query(None),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(Company).filter(Company.is_active == True)
    if search:
        q = q.filter(or_(Company.name.ilike(f"%{search}%"), Company.type.ilike(f"%{search}%")))
    return [comp_dict(c) for c in q.all()]

@router.post("/", status_code=201)
async def create_company(data: CompanyCreate, db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.warehouse))):
    c = Company(**data.dict()); db.add(c); db.commit(); db.refresh(c); return comp_dict(c)

@router.put("/{cid}")
async def update_company(cid: int, data: CompanyCreate, db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.warehouse))):
    c = db.query(Company).filter(Company.id == cid).first()
    if not c: raise HTTPException(404, "الشركة غير موجودة")
    for k, v in data.dict(exclude_unset=True).items(): setattr(c, k, v)
    db.commit(); return comp_dict(c)

@router.delete("/{cid}")
async def delete_company(cid: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))):
    c = db.query(Company).filter(Company.id == cid).first()
    if not c: raise HTTPException(404, "غير موجود")
    c.is_active = False; db.commit(); return {"message": "تم الحذف"}
