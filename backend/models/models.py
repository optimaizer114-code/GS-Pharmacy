"""
نماذج قاعدة البيانات — SQLAlchemy ORM
صيدلية الحلول العالمية
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, ForeignKey, Enum, Date, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


# ─────────────────────────────────────────────
#  Enums
# ─────────────────────────────────────────────
class UserRole(str, enum.Enum):
    admin = "admin"
    pharmacist = "pharmacist"
    warehouse = "warehouse"

class ProductCategory(str, enum.Enum):
    medicine = "medicine"
    cosmetic = "cosmetic"
    device = "device"

class SaleStatus(str, enum.Enum):
    completed = "completed"
    refunded = "refunded"
    partial = "partial"

class PaymentMethod(str, enum.Enum):
    cash = "cash"
    card = "card"
    transfer = "transfer"
    credit = "credit"

class PurchaseStatus(str, enum.Enum):
    paid = "paid"
    pending = "pending"
    partial = "partial"

class EmployeeStatus(str, enum.Enum):
    active = "active"
    leave = "leave"
    terminated = "terminated"

class ExpenseCategory(str, enum.Enum):
    rent = "إيجار المحل"
    electricity = "الكهرباء"
    water = "المياه"
    internet = "الإنترنت والاتصالات"
    advertising = "الإعلانات والتسويق"
    maintenance = "الصيانة الشهرية"
    government = "الرسوم الحكومية"
    cleaning = "مواد تنظيف"
    admin = "مصاريف إدارية"
    commissions = "عمولات ومكافآت"
    other = "أخرى"


# ─────────────────────────────────────────────
#  Users
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id          = Column(Integer, primary_key=True, index=True)
    username    = Column(String(50), unique=True, index=True, nullable=False)
    full_name   = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role        = Column(Enum(UserRole), default=UserRole.pharmacist, nullable=False)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    last_login  = Column(DateTime(timezone=True), nullable=True)

    sales       = relationship("Sale", back_populates="user")


# ─────────────────────────────────────────────
#  Companies (Suppliers)
# ─────────────────────────────────────────────
class Company(Base):
    __tablename__ = "companies"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(150), nullable=False, index=True)
    type         = Column(String(50), nullable=False)   # أدوية / تجميل / أجهزة / متعددة
    address      = Column(String(255))
    city         = Column(String(100))
    phone1       = Column(String(20))
    phone2       = Column(String(20))
    email        = Column(String(100))
    rep_name     = Column(String(100))
    rep_phone    = Column(String(20))
    payment_terms= Column(String(50), default="نقداً")
    notes        = Column(Text)
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    products     = relationship("Product", back_populates="company")
    purchases    = relationship("Purchase", back_populates="company")


# ─────────────────────────────────────────────
#  Products (Inventory)
# ─────────────────────────────────────────────
class Product(Base):
    __tablename__ = "products"

    id              = Column(Integer, primary_key=True, index=True)
    code            = Column(String(50), unique=True, index=True)
    name            = Column(String(200), nullable=False, index=True)
    name_en         = Column(String(200))
    category        = Column(Enum(ProductCategory), nullable=False)
    description     = Column(Text)

    # Stock
    quantity        = Column(Integer, default=0, nullable=False)
    min_quantity    = Column(Integer, default=10)
    unit            = Column(String(30), default="علبة")
    location        = Column(String(50))   # رف A1

    # Pricing
    cost_price      = Column(Float, default=0)
    selling_price   = Column(Float, nullable=False)

    # Medicine specific
    ingredient      = Column(String(200))   # المادة الفعالة
    dosage          = Column(String(100))   # الجرعة
    form            = Column(String(50))    # أقراص / شراب / ...
    med_category    = Column(String(100))   # مسكنات / مضادات حيوية / ...
    requires_prescription = Column(Boolean, default=False)

    # Cosmetic specific
    brand           = Column(String(100))
    cosmetic_category = Column(String(100))
    skin_type       = Column(String(50))

    # Device specific
    device_type     = Column(String(100))
    manufacturer    = Column(String(100))
    warranty        = Column(String(50))

    # Dates
    expiry_date     = Column(Date, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
    is_active       = Column(Boolean, default=True)

    # Relations
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=True)
    company         = relationship("Company", back_populates="products")
    sale_items      = relationship("SaleItem", back_populates="product")
    purchase_items  = relationship("PurchaseItem", back_populates="product")


# ─────────────────────────────────────────────
#  Customers
# ─────────────────────────────────────────────
class Customer(Base):
    __tablename__ = "customers"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(100), nullable=False, index=True)
    phone           = Column(String(20), index=True)
    area            = Column(String(150))
    date_of_birth   = Column(Date, nullable=True)
    chronic_meds    = Column(Text)       # الأدوية المزمنة
    cosmetic_prefs  = Column(Text)       # تفضيلات التجميل
    allergies       = Column(Text)       # الحساسية
    notes           = Column(Text)
    total_purchases = Column(Float, default=0)
    last_visit      = Column(Date, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    sales           = relationship("Sale", back_populates="customer")


# ─────────────────────────────────────────────
#  Sales
# ─────────────────────────────────────────────
class Sale(Base):
    __tablename__ = "sales"

    id              = Column(Integer, primary_key=True, index=True)
    invoice_number  = Column(String(50), unique=True, index=True)
    sale_date       = Column(DateTime(timezone=True), server_default=func.now())
    subtotal        = Column(Float, default=0)
    discount        = Column(Float, default=0)
    total           = Column(Float, nullable=False)
    payment_method  = Column(Enum(PaymentMethod), default=PaymentMethod.cash)
    status          = Column(Enum(SaleStatus), default=SaleStatus.completed)
    notes           = Column(Text)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    customer_id     = Column(Integer, ForeignKey("customers.id"), nullable=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=True)

    customer        = relationship("Customer", back_populates="sales")
    user            = relationship("User", back_populates="sales")
    items           = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")


class SaleItem(Base):
    __tablename__ = "sale_items"

    id          = Column(Integer, primary_key=True, index=True)
    quantity    = Column(Integer, nullable=False)
    unit_price  = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    sale_id     = Column(Integer, ForeignKey("sales.id"), nullable=False)
    product_id  = Column(Integer, ForeignKey("products.id"), nullable=False)

    sale        = relationship("Sale", back_populates="items")
    product     = relationship("Product", back_populates="sale_items")


# ─────────────────────────────────────────────
#  Purchases
# ─────────────────────────────────────────────
class Purchase(Base):
    __tablename__ = "purchases"

    id              = Column(Integer, primary_key=True, index=True)
    purchase_date   = Column(Date, nullable=False)
    invoice_ref     = Column(String(100))
    total           = Column(Float, nullable=False)
    payment_method  = Column(String(50))
    status          = Column(Enum(PurchaseStatus), default=PurchaseStatus.paid)
    notes           = Column(Text)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=True)
    company         = relationship("Company", back_populates="purchases")
    items           = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id          = Column(Integer, primary_key=True, index=True)
    product_name= Column(String(200))
    quantity    = Column(Integer, default=0)
    unit_price  = Column(Float, default=0)
    total_price = Column(Float, default=0)

    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=False)
    product_id  = Column(Integer, ForeignKey("products.id"), nullable=True)

    purchase    = relationship("Purchase", back_populates="items")
    product     = relationship("Product", back_populates="purchase_items")


# ─────────────────────────────────────────────
#  Employees
# ─────────────────────────────────────────────
class Employee(Base):
    __tablename__ = "employees"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(100), nullable=False)
    role            = Column(String(100))
    phone           = Column(String(20))
    hire_date       = Column(Date)
    base_salary     = Column(Float, default=0)
    housing_allowance = Column(Float, default=0)
    transport_allowance = Column(Float, default=0)
    other_allowances = Column(Float, default=0)
    nationality     = Column(String(50))
    status          = Column(Enum(EmployeeStatus), default=EmployeeStatus.active)
    notes           = Column(Text)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    @property
    def total_salary(self):
        return (self.base_salary + self.housing_allowance +
                self.transport_allowance + self.other_allowances)


# ─────────────────────────────────────────────
#  Expenses
# ─────────────────────────────────────────────
class Expense(Base):
    __tablename__ = "expenses"

    id              = Column(Integer, primary_key=True, index=True)
    expense_date    = Column(Date, nullable=False)
    category        = Column(String(100), nullable=False)
    description     = Column(String(300), nullable=False)
    amount          = Column(Float, nullable=False)
    payment_method  = Column(String(50))
    receipt_ref     = Column(String(100))
    created_at      = Column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────────
#  Settings
# ─────────────────────────────────────────────
class Setting(Base):
    __tablename__ = "settings"

    id      = Column(Integer, primary_key=True)
    key     = Column(String(100), unique=True, nullable=False)
    value   = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
