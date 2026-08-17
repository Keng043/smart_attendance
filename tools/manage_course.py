# -*- coding: utf-8 -*-
"""
tools/manage_course.py
--------------------------
สคริปต์จัดการ "วิชา" (Course) ในระบบ - สร้างใหม่ / ดูรายการ / ลบ
เป็นจุดเริ่มต้นแรกที่ต้องทำก่อนใช้งานเครื่องมืออื่นๆ ทั้งหมด (capture_face.py,
register_face.py, manage_schedule.py, manage_enrollment.py ล้วนต้องอ้างอิง
รหัสวิชาที่มีอยู่แล้วในระบบเท่านั้น ถ้ายังไม่ได้สร้างวิชาไว้ก่อน จะใช้งานไม่ได้)

วิธีใช้งาน:
    เพิ่มวิชาใหม่:
        python tools/manage_course.py add --code 10301385 --name "Software Engineering Project"

    ดูรายชื่อวิชาทั้งหมดในระบบ:
        python tools/manage_course.py list

    ลบวิชา (ลบ Enrollment/CourseSchedule ที่ผูกอยู่ด้วยทั้งหมด ใช้ด้วยความระมัดระวัง):
        python tools/manage_course.py remove --code 10301385
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_session  # noqa: E402
from app.models import Course, CourseSchedule, Enrollment  # noqa: E402


def add_course(course_code: str, course_name: str):
    session = get_session()
    try:
        existing = session.query(Course).filter_by(course_code=course_code).first()
        if existing is not None:
            print(f"[COURSE] วิชารหัส {course_code} มีอยู่แล้วในระบบ: {existing.course_name}")
            return

        course = Course(course_code=course_code, course_name=course_name)
        session.add(course)
        session.commit()
        print(f"[COURSE] เพิ่มวิชาใหม่สำเร็จ: {course_code} - {course_name}")
        print(
            "[COURSE] ขั้นต่อไป: ตั้งตารางเวลาเรียนด้วย "
            f"python tools/manage_schedule.py add --course {course_code} --day <วัน> --start <HH:MM> --end <HH:MM>"
        )
    finally:
        session.close()


def list_courses():
    session = get_session()
    try:
        courses = session.query(Course).all()
        if not courses:
            print("[COURSE] ยังไม่มีวิชาในระบบเลย ใช้คำสั่ง 'add' เพื่อเพิ่มวิชาแรกได้เลย")
            return

        print(f"{'รหัสวิชา':<15} {'ชื่อวิชา'}")
        print("-" * 50)
        for course in courses:
            print(f"{course.course_code:<15} {course.course_name}")
    finally:
        session.close()


def remove_course(course_code: str):
    session = get_session()
    try:
        course = session.query(Course).filter_by(course_code=course_code).first()
        if course is None:
            print(f"[COURSE] ไม่พบวิชารหัส {course_code} ในระบบ")
            return

        # ลบข้อมูลที่ผูกกับวิชานี้ก่อน (ตารางเวลา + การลงทะเบียน) กันปัญหา foreign key
        schedule_count = session.query(CourseSchedule).filter_by(course_id=course.id).delete()
        enrollment_count = session.query(Enrollment).filter_by(course_id=course.id).delete()
        session.delete(course)
        session.commit()

        print(
            f"[COURSE] ลบวิชา {course_code} เรียบร้อยแล้ว "
            f"(ลบตารางเวลา {schedule_count} รายการ, ลงทะเบียน {enrollment_count} รายการที่ผูกอยู่ด้วย)"
        )
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="จัดการวิชาในระบบ")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    p_add = subparsers.add_parser("add", help="เพิ่มวิชาใหม่")
    p_add.add_argument("--code", required=True, help="รหัสวิชา เช่น 10301385")
    p_add.add_argument("--name", required=True, help="ชื่อวิชา เช่น 'Software Engineering Project'")

    subparsers.add_parser("list", help="ดูรายชื่อวิชาทั้งหมด")

    p_remove = subparsers.add_parser("remove", help="ลบวิชา (ลบข้อมูลที่ผูกอยู่ด้วยทั้งหมด)")
    p_remove.add_argument("--code", required=True, help="รหัสวิชาที่จะลบ")

    args = parser.parse_args()

    if args.cmd == "add":
        add_course(args.code, args.name)
    elif args.cmd == "list":
        list_courses()
    elif args.cmd == "remove":
        remove_course(args.code)


if __name__ == "__main__":
    main()
