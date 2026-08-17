# -*- coding: utf-8 -*-
"""
tools/manage_schedule.py
----------------------------
สคริปต์จัดการ "ตารางเวลาเรียน" ของแต่ละวิชา (CourseSchedule)
ระบบใช้ตารางนี้ตัดสินว่า "ขณะนี้เป็นคาบเรียนของวิชาไหน" โดยอัตโนมัติ
(ดู app/schedule_service.py) จึงต้องตั้งให้ตรงกับเวลาสอนจริงเสมอ

วิธีใช้งาน:

  เพิ่มตารางเรียน (1 วิชาเพิ่มได้หลายวัน เรียกซ้ำได้หลายครั้ง):
      python tools/manage_schedule.py add --course 10301385 --day monday --start 09:00 --end 12:00
      python tools/manage_schedule.py add --course 10301385 --day wednesday --start 09:00 --end 12:00

  ลบตารางเรียนเดิมทั้งหมดของวิชา (ใช้ก่อน add ใหม่ ถ้าต้องการเริ่มนับใหม่):
      python tools/manage_schedule.py clear --course 10301385

  ดูตารางเรียนทั้งหมดในระบบ:
      python tools/manage_schedule.py list

ชื่อวันที่ใช้ได้ (--day): monday, tuesday, wednesday, thursday, friday, saturday, sunday
รูปแบบเวลา (--start / --end): HH:MM แบบ 24 ชั่วโมง เช่น 09:00, 13:30
"""

import os
import sys
import argparse
from datetime import time as time_cls

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_session  # noqa: E402
from app.models import Course, CourseSchedule  # noqa: E402
from app.schedule_service import ScheduleService, THAI_DAY_NAMES  # noqa: E402

DAY_NAME_TO_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def parse_time(value: str) -> time_cls:
    hour_str, minute_str = value.split(":")
    return time_cls(int(hour_str), int(minute_str))


def add_schedule(course_code: str, day: str, start: str, end: str):
    session = get_session()
    try:
        course = session.query(Course).filter_by(course_code=course_code).first()
        if course is None:
            print(f"[SCHEDULE] ไม่พบวิชารหัส {course_code} ในระบบ")
            return

        day_index = DAY_NAME_TO_INDEX[day.lower()]
        schedule = CourseSchedule(
            course_id=course.id,
            day_of_week=day_index,
            start_time=parse_time(start),
            end_time=parse_time(end),
        )
        session.add(schedule)
        session.commit()
        print(
            f"[SCHEDULE] เพิ่มตารางเรียนวิชา {course.course_code} แล้ว: "
            f"วัน{THAI_DAY_NAMES[day_index]} {start}-{end}"
        )
    finally:
        session.close()


def clear_schedule(course_code: str):
    session = get_session()
    try:
        course = session.query(Course).filter_by(course_code=course_code).first()
        if course is None:
            print(f"[SCHEDULE] ไม่พบวิชารหัส {course_code} ในระบบ")
            return

        deleted_count = (
            session.query(CourseSchedule).filter_by(course_id=course.id).delete()
        )
        session.commit()
        print(f"[SCHEDULE] ลบตารางเรียนเดิมของ {course.course_code} ไปแล้ว {deleted_count} รายการ")
    finally:
        session.close()


def list_schedules():
    schedules = ScheduleService().get_all_schedules_display()
    if not schedules:
        print("[SCHEDULE] ยังไม่มีตารางเรียนตั้งไว้เลย")
        return

    print(f"{'รหัสวิชา':<12} {'ชื่อวิชา':<28} {'วัน':<10} {'เวลา'}")
    print("-" * 70)
    for item in schedules:
        time_range = f"{item['start_time']}-{item['end_time']}"
        print(f"{item['course_code']:<12} {item['course_name']:<28} {item['day_name']:<10} {time_range}")


def main():
    parser = argparse.ArgumentParser(description="จัดการตารางเวลาเรียนของแต่ละวิชา")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    p_add = subparsers.add_parser("add", help="เพิ่มตารางเรียน")
    p_add.add_argument("--course", required=True, help="รหัสวิชา เช่น 10301385")
    p_add.add_argument("--day", required=True, choices=list(DAY_NAME_TO_INDEX.keys()))
    p_add.add_argument("--start", required=True, help="เวลาเริ่ม เช่น 09:00")
    p_add.add_argument("--end", required=True, help="เวลาจบ เช่น 12:00")

    p_clear = subparsers.add_parser("clear", help="ลบตารางเรียนเดิมทั้งหมดของวิชา")
    p_clear.add_argument("--course", required=True, help="รหัสวิชา เช่น 10301385")

    subparsers.add_parser("list", help="ดูตารางเรียนทั้งหมดในระบบ")

    args = parser.parse_args()

    if args.cmd == "add":
        add_schedule(args.course, args.day, args.start, args.end)
    elif args.cmd == "clear":
        clear_schedule(args.course)
    elif args.cmd == "list":
        list_schedules()


if __name__ == "__main__":
    main()