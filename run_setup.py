# -*- coding: utf-8 -*-
"""
run_setup.py
-------------
สคริปต์นี้ใช้สำหรับ "ติดตั้งฐานข้อมูลครั้งแรก" ของโปรเจกต์
รันคำสั่งนี้จาก root ของโปรเจกต์ (โฟลเดอร์ smart_attendance/) ด้วยคำสั่ง:

    python run_setup.py

จะทำ 2 อย่างตามลำดับ:
1. สร้างไฟล์ attendance.db และตารางทั้งหมดตามที่ประกาศใน app/models.py
2. ใส่ข้อมูลจำลอง (Mock Data) เข้าไป เพื่อให้พร้อมทดสอบ/พรีเซนต์ทันที
"""

from app.database import init_db
from app.seed_data import seed_mock_data

# ต้อง import models ก่อนเรียก init_db() เสมอ
# เพื่อให้ SQLAlchemy รู้จักคลาส Student, Course, ฯลฯ ที่ inherit จาก Base
from app import models  # noqa: F401  (import ไว้เพื่อ side-effect การลงทะเบียน Model)


def main():
    print("[SETUP] กำลังสร้างตารางในฐานข้อมูล ...")
    init_db()
    print("[SETUP] สร้างตารางสำเร็จ -> attendance.db")

    print("[SETUP] กำลังใส่ข้อมูลจำลอง (Mock Data) ...")
    seed_mock_data()
    print("[SETUP] เสร็จสิ้น! พร้อมใช้งานสำหรับ Phase ถัดไป")


if __name__ == "__main__":
    main()
