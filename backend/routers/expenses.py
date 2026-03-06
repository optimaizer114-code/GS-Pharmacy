"""المصروفات"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from pydantic import BaseModel
from core.database import get_db
from core.security import get_current_user, require_roles
from models.models import Expense, User, UserRole

router = APIRouter()

class ExpenseCreate(BaseModel):
    expense_date: date
    category: str
    description: str
    amount: float
    payment_method: str = "نقداً"
    receipt_ref: Optional[str] = None

@router.get("/")
async def get_expenses(
    year: Optional[int] = Query(None), month: Optional[int] = Query(None),
    page: int = 1, limit: int = 100,
    db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.admin))):
    from sqlalchemy import extract
    q = db.query(Expense)
    if year: q = q.filter(extract("year", Expense.expense_date) == year)
    if month: q = q.filter(extract("month", Expense.expense_date) == month)
    total = q.count()
    items = q.order_by(Expense.expense_date.desc()).offset((page-1)*limit).limit(limit).all()
    return {"total": total, "data": [
        {"id": e.id, "date": str(e.expense_date), "category": e.category,
         "description": e.description, "amount": e.amount,
         "payment_method": e.payment_method, "receipt_ref": e.receipt_ref}
        for e in items
    ]}

@router.post("/", status_code=201)
async def create_expense(data: ExpenseCreate, db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))):
    e = Expense(**data.dict()); db.add(e); db.commit(); db.refresh(e)
    return {"id": e.id, "message": "تم حفظ المصروف"}

@router.delete("/{eid}")
async def delete_expense(eid: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))):
    e = db.query(Expense).filter(Expense.id == eid).first()
    if not e: raise HTTPException(404, "غير موجود")
    db.delete(e); db.commit(); return {"message": "تم الحذف"}
