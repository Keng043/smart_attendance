# -*- coding: utf-8 -*-
"""
tools/check_students.py
--------------------------
สคริปต์ตรวจสอบด่วน: แสดงรายชื่อนักศึกษาทั้งหมดในระบบตอนนี้ พร้อม path รูปที่ผูกอยู่
และ "รายวิชาที่ลงทะเบียนไว้" (Enrollment) เพื่อเช็คว่าใครมีสิทธิ์เช็คชื่อวิชาไหนได้บ้าง
ใช้เวลาข้อมูลดูแปลก ๆ (เช่น จำหน้าผิดคน / จำหน้าตัวเองไม่ได้ / เช็คชื่อไม่ผ่าน)

วิธีใช้:
    python tools/check_students.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_session  # noqa: E402
from app.models import Student, Enrollment, Course  # noqa: E402


def main():
    session = get_session()
    try:
        students = session.query(Student).all()

        if not students:
            print("[CHECK] ยังไม่มีนักศึกษาในระบบเลย")
            return

        print(f"{'รหัสนักศึกษา':<15} {'ชื่อ':<25} {'Path รูปใบหน้า'}")
        print("-" * 90)

        for student in students:
            path = student.face_image_path or "(ไม่มี)"
            exists_flag = "✔" if student.face_image_path and os.path.exists(student.face_image_path) else "✘"
            print(f"{student.student_code:<15} {student.full_name:<25} [{exists_flag}] {path}")

            # ดึงรายวิชาที่นักศึกษาคนนี้ลงทะเบียนไว้ (join Enrollment -> Course)
            enrollments = (
                session.query(Course)
                .join(Enrollment, Enrollment.course_id == Course.id)
                .filter(Enrollment.student_id == student.id)
                .all()
            )
            if enrollments:
                course_list = ", ".join(f"{c.course_code} ({c.course_name})" for c in enrollments)
                print(f"{'':<15} {'':<25} ↳ ลงทะเบียนวิชา: {course_list}")
            else:
                print(f"{'':<15} {'':<25} ↳ ยังไม่ได้ลงทะเบียนวิชาไหนเลย")

        print("-" * 90)
        print("✔ = พบไฟล์รูปจริงในเครื่อง | ✘ = ไม่พบไฟล์ (path ผิด หรือไฟล์ถูกลบ/ย้าย)")
    finally:
        session.close()


if __name__ == "__main__":
    main()