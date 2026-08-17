# -*- coding: utf-8 -*-
"""
tools/manage_instructor.py
------------------------------
สคริปต์จัดการบัญชีอาจารย์ (สร้างใหม่ / เปลี่ยนรหัสผ่าน)

วิธีใช้งาน:
    python tools/manage_instructor.py --username instructor --password "รหัสผ่านใหม่"
    python tools/manage_instructor.py --username instructor --password "รหัสผ่านใหม่" --name "อาจารย์สมชาย"

ถ้า username ที่ระบุยังไม่มีในระบบ -> สร้างบัญชีใหม่
ถ้ามีอยู่แล้ว -> อัปเดตรหัสผ่าน (และชื่อ ถ้าระบุ --name มาด้วย)

⚠️ ควรเปลี่ยนรหัสผ่านเริ่มต้น (instructor / instructor123) ทันทีก่อนใช้งานจริง
"""

import os
import sys
import argparse

from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_session  # noqa: E402
from app.models import Instructor  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="จัดการบัญชีอาจารย์ (สร้างใหม่/เปลี่ยนรหัสผ่าน)")
    parser.add_argument("--username", required=True, help="ชื่อผู้ใช้สำหรับ Login")
    parser.add_argument("--password", required=True, help="รหัสผ่านใหม่ (จะถูก hash ก่อนบันทึก)")
    parser.add_argument("--name", required=False, help="ชื่อแสดงผล เช่น 'อาจารย์สมชาย'")
    args = parser.parse_args()

    session = get_session()
    try:
        instructor = session.query(Instructor).filter_by(username=args.username).first()

        if instructor is None:
            instructor = Instructor(
                username=args.username,
                password_hash=generate_password_hash(args.password),
                full_name=args.name or args.username,
            )
            session.add(instructor)
            session.commit()
            print(f"[INSTRUCTOR] สร้างบัญชีใหม่สำเร็จ: {args.username}")
        else:
            instructor.password_hash = generate_password_hash(args.password)
            if args.name:
                instructor.full_name = args.name
            session.commit()
            print(f"[INSTRUCTOR] เปลี่ยนรหัสผ่านของ {args.username} สำเร็จแล้ว")
    finally:
        session.close()


if __name__ == "__main__":
    main()