"""إعداد قاعدة البيانات"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://pharmacy_user:StrongPass123!@localhost:5432/pharmacy_db"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """إنشاء الجداول + بيانات أولية"""
    from models.models import Base
    Base.metadata.create_all(bind=engine)
    seed_initial_data()


def seed_initial_data():
    """بيانات أولية: مستخدم admin افتراضي"""
    from models.models import User, UserRole, Setting
    from core.security import get_password_hash

    db = SessionLocal()
    try:
        # Admin user
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                full_name="مدير النظام",
                hashed_password=get_password_hash("admin123"),
                role=UserRole.admin,
                is_active=True
            )
            db.add(admin)

        # Pharmacist user
        if not db.query(User).filter(User.username == "pharmacist").first():
            ph = User(
                username="pharmacist",
                full_name="الصيدلاني",
                hashed_password=get_password_hash("ph1234"),
                role=UserRole.pharmacist,
                is_active=True
            )
            db.add(ph)

        # Warehouse user
        if not db.query(User).filter(User.username == "warehouse").first():
            wh = User(
                username="warehouse",
                full_name="مسؤول المخزن",
                hashed_password=get_password_hash("wh2222"),
                role=UserRole.warehouse,
                is_active=True
            )
            db.add(wh)

        # Default settings
        defaults = {
            "pharmacy_name": "صيدلية الحلول العالمية",
            "pharmacy_logo_emoji": "⚕️",
            "invoice_counter": "1000",
            "low_stock_threshold": "10",
        }
        for key, val in defaults.items():
            if not db.query(Setting).filter(Setting.key == key).first():
                db.add(Setting(key=key, value=val))

        db.commit()
        print("✅ Initial data seeded successfully")
    except Exception as e:
        db.rollback()
        print(f"❌ Seed error: {e}")
    finally:
        db.close()
