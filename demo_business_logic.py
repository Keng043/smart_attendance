# -*- coding: utf-8 -*-
"""
demo_business_logic.py
--------------------------
ทดสอบ Business Logic + Timer แบบอัตโนมัติ (Auto Detect, กล้องเดียว)
โดยไม่ต้องใช้กล้องจริง จำลองว่า Facial Recognition "จำหน้าได้แล้ว"
แล้วส่ง student_id เข้ามาที่ AttendanceController.handle_face_detected() ตรงๆ

Sequence ที่จำลอง (เดินผ่านกล้องหน้าประตู 3 ครั้ง):
    1. เดินผ่านครั้งที่ 1 (ครั้งแรก)      -> ระบบตีความว่า "เข้าห้อง" -> เช็คชื่อ (IN_CLASS)
    2. เดินผ่านครั้งที่ 2 (อยู่ในห้องแล้ว) -> ระบบตีความว่า "ออกจากห้อง" -> AWAY เริ่มจับเวลา
    3. รอเกิน AWAY_TIMEOUT_SECONDS โดยไม่เดินผ่านกล้องอีก
    4. TimeoutMonitor ตรวจพบว่าเกินเวลา   -> เปลี่ยนเป็น MISSING + แจ้งเตือน [ALERT]
    5. เดินผ่านครั้งที่ 3 (กลับมาแล้ว)    -> ระบบตีความว่า "เข้าห้อง" -> กลับเป็น IN_CLASS

วิธีรัน:
    python demo_business_logic.py
"""

import time

from app.attendance_controller import AttendanceController
from app.timeout_monitor import TimeoutMonitor
from app.config import AWAY_TIMEOUT_SECONDS
from app.database import get_session
from app.models import Student


def get_kongkiat_id() -> int:
    session = get_session()
    try:
        student = session.query(Student).filter_by(student_code="6704101306").first()
        if student is None:
            raise RuntimeError(
                "ไม่พบนักศึกษารหัส 6704101306 (Kongkiat_J) ในระบบ "
                "กรุณารัน 'python run_setup.py' ก่อนเทสไฟล์นี้"
            )
        return student.id
    finally:
        session.close()


def print_step(step_number: int, description: str):
    print("\n" + "=" * 65)
    print(f"STEP {step_number}: {description}")
    print("=" * 65)


def main():
    controller = AttendanceController()
    monitor = TimeoutMonitor(controller=controller)
    student_id = get_kongkiat_id()

    print_step(1, "เดินผ่านกล้องครั้งที่ 1 (ครั้งแรก) -> คาดว่าเป็นการเข้าห้อง")
    result = controller.handle_face_detected(student_id)
    print(f"  ผลลัพธ์: {result['message']}")

    monitor.start()

    print_step(2, "เดินผ่านกล้องครั้งที่ 2 (อยู่ในห้องแล้ว) -> คาดว่าเป็นการออกจากห้อง")
    result = controller.handle_face_detected(student_id)
    print(f"  ผลลัพธ์: {result['message']}")

    print_step(
        3,
        f"รอเกินเวลาที่กำหนด ({AWAY_TIMEOUT_SECONDS} วินาที) โดยไม่เดินผ่านกล้องอีก ...\n"
        f"          (ระหว่างนี้ TimeoutMonitor จะตรวจสอบเบื้องหลังทุก 2 วินาที)",
    )
    time.sleep(AWAY_TIMEOUT_SECONDS + 3)
    print("  -> ถ้าเห็นข้อความ [ALERT] ด้านบน แสดงว่าระบบตีสถานะ Missing สำเร็จแล้ว")

    print_step(4, "เดินผ่านกล้องครั้งที่ 3 (กลับมาแล้ว) -> คาดว่ากลับเข้าห้อง")
    result = controller.handle_face_detected(student_id)
    print(f"  ผลลัพธ์: {result['message']}")

    monitor.stop()
    print("\n[DEMO] ทดสอบ Business Logic แบบอัตโนมัติครบทุกสถานการณ์แล้ว")


if __name__ == "__main__":
    main()