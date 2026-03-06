"""إدارة المبيعات ونقطة البيع"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel

from core.database import get_db
from core.security import get_current_user, require_roles
from models.models import Sale, SaleItem, Product, Customer, User, UserRole, Setting, PaymentMethod, SaleStatus

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────
class SaleItemIn(BaseModel):
    product_id: int
    quantity: int
    unit_price: float

class SaleCreate(BaseModel):
    items: List[SaleItemIn]
    customer_id: Optional[int] = None
    discount: float = 0
    payment_method: PaymentMethod = PaymentMethod.cash
    notes: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────
def sale_to_dict(s: Sale) -> dict:
    return {
        "id": s.id,
        "invoice_number": s.invoice_number,
        "sale_date": s.sale_date.isoformat() if s.sale_date else None,
        "subtotal": s.subtotal,
        "discount": s.discount,
        "total": s.total,
        "payment_method": s.payment_method,
        "status": s.status,
        "notes": s.notes,
        "customer_id": s.customer_id,
        "customer_name": s.customer.name if s.customer else "عميل عام",
        "user_id": s.user_id,
        "user_name": s.user.full_name if s.user else None,
        "items": [
            {
                "product_id": i.product_id,
                "product_name": i.product.name if i.product else "",
                "quantity": i.quantity,
                "unit_price": i.unit_price,
                "total_price": i.total_price,
            }
            for i in s.items
        ],
    }

def get_next_invoice_number(db: Session) -> str:
    setting = db.query(Setting).filter(Setting.key == "invoice_counter").first()
    counter = int(setting.value) + 1 if setting else 1001
    if setting:
        setting.value = str(counter)
    else:
        db.add(Setting(key="invoice_counter", value=str(counter)))
    return f"INV-{counter}"


# ─── Endpoints ────────────────────────────────────────────
@router.get("/")
async def get_sales(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    customer_id: Optional[int] = Query(None),
    payment_method: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Sale).options(
        joinedload(Sale.customer),
        joinedload(Sale.user),
        joinedload(Sale.items).joinedload(SaleItem.product)
    )
    if date_from:
        query = query.filter(func.date(Sale.sale_date) >= date_from)
    if date_to:
        query = query.filter(func.date(Sale.sale_date) <= date_to)
    if customer_id:
        query = query.filter(Sale.customer_id == customer_id)
    if payment_method:
        query = query.filter(Sale.payment_method == payment_method)

    total = query.count()
    sales = query.order_by(Sale.sale_date.desc()).offset((page-1)*limit).limit(limit).all()
    return {"total": total, "data": [sale_to_dict(s) for s in sales]}


@router.get("/today-summary")
async def today_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    sales = db.query(Sale).filter(func.date(Sale.sale_date) == today).all()
    total = sum(s.total for s in sales)
    return {
        "count": len(sales),
        "total": total,
        "by_payment": {
            pm: sum(s.total for s in sales if s.payment_method == pm)
            for pm in set(s.payment_method for s in sales)
        }
    }


@router.get("/{sale_id}")
async def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    s = db.query(Sale).options(
        joinedload(Sale.customer),
        joinedload(Sale.items).joinedload(SaleItem.product)
    ).filter(Sale.id == sale_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")
    return sale_to_dict(s)


@router.post("/", status_code=201)
async def create_sale(
    data: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate items and stock
    subtotal = 0
    items_data = []
    for item in data.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"المنتج {item.product_id} غير موجود")
        if product.quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"الكمية المتاحة من {product.name} هي {product.quantity} فقط"
            )
        line_total = item.unit_price * item.quantity
        subtotal += line_total
        items_data.append((product, item, line_total))

    total = max(0, subtotal - data.discount)
    invoice_no = get_next_invoice_number(db)

    sale = Sale(
        invoice_number=invoice_no,
        customer_id=data.customer_id,
        user_id=current_user.id,
        subtotal=subtotal,
        discount=data.discount,
        total=total,
        payment_method=data.payment_method,
        notes=data.notes,
    )
    db.add(sale)
    db.flush()

    for product, item, line_total in items_data:
        db.add(SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=line_total,
        ))
        product.quantity -= item.quantity

    # Update customer totals
    if data.customer_id:
        customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
        if customer:
            customer.total_purchases = (customer.total_purchases or 0) + total
            customer.last_visit = date.today()

    db.commit()
    db.refresh(sale)

    return sale_to_dict(
        db.query(Sale).options(
            joinedload(Sale.customer),
            joinedload(Sale.items).joinedload(SaleItem.product)
        ).filter(Sale.id == sale.id).first()
    )


@router.delete("/{sale_id}")
async def delete_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))
):
    s = db.query(Sale).filter(Sale.id == sale_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")
    # Restore stock
    for item in s.items:
        if item.product:
            item.product.quantity += item.quantity
    db.delete(s)
    db.commit()
    return {"message": "تم حذف الفاتورة واسترجاع المخزون"}
