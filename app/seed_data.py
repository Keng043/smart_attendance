# -*- coding: utf-8 -*-
"""
app/seed_data.py
------------------
ไฟล์นี้รับผิดชอบการ "ใส่ข้อมูลตั้งต้นที่จำเป็นขั้นต่ำสุด" เข้าไปในฐานข้อมูล

**อัปเดต (โหมดข้อมูลจริงทั้งหมด):**
ไม่สร้างข้อมูลจำลอง (นักศึกษา/วิชา/ตารางเวลา) ให้อีกต่อไป เพราะผู้ใช้ต้องการ
กรอกข้อมูลจริงเองทั้งหมดผ่านเครื่องมือใน tools/ ไฟล์นี้จะสร้างแค่สิ่งที่
"จำเป็นต้องมีก่อนใช้งานได้" เท่านั้น คือบัญชีอาจารย์สำหรับ Login (ถ้าไม่มี
บัญชีนี้เลย จะเข้า Dashboard ไม่ได้ตั้งแต่ต้น เพราะไม่มีระบบสมัครสมาชิกเอง)

วิธีเพิ่มข้อมูลจริงหลังรันไฟล์นี้ (ดูรายละเอียดคำสั่งได้จาก tools/ ทุกไฟล์):
    1. python tools/manage_course.py add --code <รหัสวิชา> --name "<ชื่อวิชา>"
    2. python tools/manage_schedule.py add --course <รหัสวิชา> --day <วัน> --start <HH:MM> --end <HH:MM>
    3. python tools/capture_face.py --code <รหัสนักศึกษา> --name "<ชื่อ>" --course <รหัสวิชา>

ฟังก์ชันนี้เช็คก่อนว่ามีบัญชีอาจารย์อยู่แล้วหรือยัง เพื่อป้องกันการ insert ซ้ำ (idempotent)
"""

from werkzeug.security import generate_password_hash

from app.database import get_session
from app.models import Instructor


def seed_mock_data():
    """
    สร้างบัญชีอาจารย์เริ่มต้น 1 บัญชี (ถ้ายังไม่มีเลย) เพื่อให้ Login เข้า
    Dashboard ได้ตั้งแต่ครั้งแรกที่รันระบบ ไม่สร้างข้อมูลนักศึกษา/วิชา/ตารางเวลา
    ใดๆ ทั้งสิ้น (ผู้ใช้กรอกข้อมูลจริงเองผ่านเครื่องมือใน tools/)

    ⚠️ เปลี่ยนรหัสผ่านเริ่มต้นทันทีด้วย:
        python tools/manage_instructor.py --username instructor --password "รหัสผ่านใหม่"
    """
    session = get_session()

    try:
        existing_count = session.query(Instructor).count()
        if existing_count > 0:
            print(f"[SEED] พบบัญชีอาจารย์อยู่แล้ว {existing_count} บัญชี -> ข้ามการ Seed")
            return

        default_instructor = Instructor(
            username="instructor",
            password_hash=generate_password_hash("instructor123"),
            full_name="อาจารย์ผู้สอน",
        )
        session.add(default_instructor)
        session.commit()

        print("[SEED] สร้างบัญชีอาจารย์เริ่มต้นสำเร็จ: username=instructor, password=instructor123")
        print("[SEED] ⚠️ กรุณาเปลี่ยนรหัสผ่านทันทีด้วย: python tools/manage_instructor.py --username instructor --password <รหัสใหม่>")
        print("[SEED] ไม่มีข้อมูลนักศึกษา/วิชา/ตารางเวลาเลย ต้องเพิ่มเองผ่านเครื่องมือใน tools/")

    except Exception as e:
        session.rollback()
        print(f"[SEED] เกิดข้อผิดพลาดระหว่าง Seed ข้อมูล: {e}")
        raise
    finally:
        session.close()