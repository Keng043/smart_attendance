# -*- coding: utf-8 -*-
"""
app/database.py
-----------------
ไฟล์นี้รับผิดชอบเรื่อง "การเชื่อมต่อฐานข้อมูล" เพียงอย่างเดียว
(Single Responsibility Principle - SRP)

- สร้าง Engine เชื่อมต่อ SQLite
- สร้าง SessionLocal สำหรับเปิด Session คุยกับ DB
- สร้าง Base Class ให้ Models ต่าง ๆ นำไป inherit

การแยกไฟล์นี้ออกจาก models.py ทำให้:
1. ถ้าต้องเปลี่ยนจาก SQLite -> PostgreSQL ในอนาคต แก้ที่นี่ที่เดียว
2. Models ไม่ต้องรู้ว่า DB จริง ๆ คืออะไร (Dependency Inversion)
"""

import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

# ----------------------------------------------------------------
# กำหนด Path ของไฟล์ Database ให้อยู่ที่ root ของโปรเจกต์เสมอ
# ไม่ว่าจะรันสคริปต์จากที่ไหนก็ตาม (ป้องกันปัญหา relative path)
# ----------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, "attendance.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# echo=False ปิด log SQL ที่ SQLAlchemy พ่นออกมา (เปิดเป็น True ได้ตอน debug)
# connect_args จำเป็นสำหรับ SQLite เมื่อใช้งานร่วมกับ Flask (multi-thread)
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

# SessionLocal คือ "โรงงานผลิต Session" แต่ละครั้งที่เรียก SessionLocal()
# จะได้ Session ใหม่ 1 อัน สำหรับคุยกับ DB ในแต่ละ Request/Transaction
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Base คือคลาสตั้งต้นที่ Models ทุกตัว (Student, AttendanceLog, ...)
# ต้อง inherit ไปใช้ เพื่อให้ SQLAlchemy รู้จักและสร้างตารางให้อัตโนมัติ
Base = declarative_base()


def init_db():
    """
    สร้างตารางทั้งหมดในฐานข้อมูล ตาม Models ที่ inherit จาก Base
    ต้อง import models ก่อนเรียกฟังก์ชันนี้ (ทำใน run_setup.py)
    """
    Base.metadata.create_all(bind=engine)

    # Lightweight SQLite migration for existing installations. create_all() does
    # not alter an existing table, so add the new Instructor.role column explicitly.
    inspector = inspect(engine)
    if "instructors" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("instructors")}
        if "role" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE instructors ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'INSTRUCTOR'"))


def get_session():
    """
    Helper function สำหรับขอ Session ใหม่มาใช้งาน
    ตัวอย่างการใช้งาน:
        session = get_session()
        students = session.query(Student).all()
        session.close()
    """
    return SessionLocal()
