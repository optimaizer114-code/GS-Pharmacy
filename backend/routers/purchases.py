"""المشتريات"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from pydantic import BaseModel

from core.database import get_db
from core.security import get_current_user, require_roles
from models.models import Purchase, PurchaseItem, User, UserRole, PurchaseStatus

router = APIRouter()

class PurchaseItemIn(BaseModel):
    product_id: Optional[int] = None
    product_name: str
    quantity: int = 0
    unit_price: float = 0

class PurchaseCreate(BaseModel):
    purchase_date: date
    company_id: Optional[int] = None
    invoice_ref: Optional[str] = None
    total: float
    payment_method: str = "نقداً"
    status: PurchaseStatus = PurchaseStatus.paid
    notes: Optional[str] = None
    items: List[PurchaseItemIn] = []

@router.get("/")
async def get_purchases(
    page: int = Query(1), limit: int = Query(50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Purchase)
    total = query.count()
    items = query.order_by(Purchase.purchase_date.desc()).offset((page-1)*limit).limit(limit).all()
    return {"total": total, "data": [
        {"id": p.id, "purchase_date": str(p.purchase_date), "invoice_ref": p.invoice_ref,
         "company_name": p.company.name if p.company else None, "total": p.total,
         "payment_method": p.payment_method, "status": p.status, "notes": p.notes}
        for p in items
    ]}

@router.post("/", status_code=201)
async def create_purchase(
    data: PurchaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.warehouse))
):
    p = Purchase(**data.dict(exclude={"items"}))
    db.add(p)
    db.flush()
    for item in data.items:
        db.add(PurchaseItem(purchase_id=p.id, **item.dict()))
    db.commit()
    return {"id": p.id, "message": "تم حفظ فاتورة الشراء"}

@router.delete("/{pid}")
async def delete_purchase(
    pid: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))
):
    p = db.query(Purchase).filter(Purchase.id == pid).first()
    if not p: raise HTTPException(404, "غير موجود")
    db.delete(p); db.commit()
    return {"message": "تم الحذف"}
