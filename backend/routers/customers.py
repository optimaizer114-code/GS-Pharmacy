"""العملاء"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from datetime import date
from pydantic import BaseModel
from core.database import get_db
from core.security import get_current_user, require_roles
from models.models import Customer, User, UserRole

router = APIRouter()

class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    area: Optional[str] = None
    date_of_birth: Optional[date] = None
    chronic_meds: Optional[str] = None
    cosmetic_prefs: Optional[str] = None
    allergies: Optional[str] = None
    notes: Optional[str] = None

def cust_dict(c):
    return {"id": c.id, "name": c.name, "phone": c.phone, "area": c.area,
            "chronic_meds": c.chronic_meds, "cosmetic_prefs": c.cosmetic_prefs,
            "allergies": c.allergies, "notes": c.notes,
            "total_purchases": c.total_purchases, "last_visit": str(c.last_visit) if c.last_visit else None}

@router.get("/")
async def get_customers(search: Optional[str] = Query(None), page: int = 1, limit: int = 50,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(Customer)
    if search:
        q = q.filter(or_(Customer.name.ilike(f"%{search}%"), Customer.phone.ilike(f"%{search}%")))
    return {"total": q.count(), "data": [cust_dict(c) for c in q.offset((page-1)*limit).limit(limit).all()]}

@router.post("/", status_code=201)
async def create_customer(data: CustomerCreate, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    c = Customer(**data.dict()); db.add(c); db.commit(); db.refresh(c)
    return cust_dict(c)

@router.put("/{cid}")
async def update_customer(cid: int, data: CustomerCreate, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    c = db.query(Customer).filter(Customer.id == cid).first()
    if not c: raise HTTPException(404, "العميل غير موجود")
    for k, v in data.dict(exclude_unset=True).items(): setattr(c, k, v)
    db.commit(); return cust_dict(c)

@router.delete("/{cid}")
async def delete_customer(cid: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))):
    c = db.query(Customer).filter(Customer.id == cid).first()
    if not c: raise HTTPException(404, "غير موجود")
    db.delete(c); db.commit(); return {"message": "تم الحذف"}
