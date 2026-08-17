# -*- coding: utf-8 -*-
"""
tools/manage_enrollment.py
------------------------------
สคริปต์ช่วยจัดการการลงทะเบียนวิชาของนักศึกษา (เพิ่ม/ถอนออก)
ใช้ตอนต้องการทดสอบสถานการณ์ "ไม่ได้ลงทะเบียน" หรือแก้ไขข้อมูลลงทะเบียนผิดพลาด

วิธีใช้:
    python tools/manage_enrollment.py --code 6704101334 --course 1030199 --action unenroll
    python tools/manage_enrollment.py --code 6704101334 --course 1030199 --action enroll
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_session  # noqa: E402
from app.models import Student, Enrollment, Course  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="จัดการการลงทะเบียนวิชาของนักศึกษา")
    parser.add_argument("--code", required=True, help="รหัสนักศึกษา")
    parser.add_argument("--course", required=True, help="รหัสวิชา เช่น 10301385")
    parser.add_argument(
        "--action", required=True, choices=["enroll", "unenroll"],
        help="enroll = ลงทะเบียนวิชา, unenroll = ถอนออกจากวิชา",
    )
    args = parser.parse_args()

    session = get_session()
    try:
        student = session.query(Student).filter_by(student_code=args.code).first()
        if student is None:
            print(f"[ENROLLMENT] ไม่พบนักศึกษารหัส {args.code} ในระบบ")
            return

        course = session.query(Course).filter_by(course_code=args.course).first()
        if course is None:
            print(f"[ENROLLMENT] ไม่พบวิชารหัส {args.course} ในระบบ")
            return

        existing = (
            session.query(Enrollment)
            .filter_by(student_id=student.id, course_id=course.id)
            .first()
        )

        if args.action == "unenroll":
            if existing is None:
                print(f"[ENROLLMENT] {student.full_name} ไม่ได้ลงทะเบียนวิชา {course.course_code} อยู่แล้ว (ไม่ต้องทำอะไร)")
            else:
                session.delete(existing)
                session.commit()
                print(f"[ENROLLMENT] ถอน {student.full_name} ออกจากวิชา {course.course_code} เรียบร้อยแล้ว")
        else:  # enroll
            if existing is not None:
                print(f"[ENROLLMENT] {student.full_name} ลงทะเบียนวิชา {course.course_code} อยู่แล้ว (ไม่ต้องทำอะไร)")
            else:
                session.add(Enrollment(student_id=student.id, course_id=course.id))
                session.commit()
                print(f"[ENROLLMENT] ลงทะเบียน {student.full_name} เข้าวิชา {course.course_code} เรียบร้อยแล้ว")
    finally:
        session.close()


if __name__ == "__main__":
    main()