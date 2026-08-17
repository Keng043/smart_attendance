# -*- coding: utf-8 -*-
"""
app/schedule_service.py
--------------------------
ระบบตอนนี้รองรับ "หลายวิชา" พร้อมกัน (ก่อนหน้านี้ fix ไว้วิชาเดียวผ่าน
DEFAULT_COURSE_ID) จึงต้องมีตัวกลางที่ตอบคำถามว่า "ขณะนี้เวลานี้ ตรงกับ
คาบเรียนของวิชาไหน" โดยอ้างอิงจากตาราง CourseSchedule (วัน + เวลาเริ่ม/จบ
ของแต่ละวิชา)

แยกออกมาเป็น Service ต่างหาก (ไม่ยัดใส่ใน AttendanceController) ตามหลัก SRP:
- ScheduleService รับผิดชอบแค่ "ตอบว่าตอนนี้เป็นคาบของวิชาไหน"
- AttendanceController ไปเรียกใช้ผลลัพธ์นี้ต่อ เพื่อเช็คสิทธิ์ Enrollment

ข้อจำกัดที่ควรรู้: ถ้าตารางเวลาของ 2 วิชาซ้อนกัน (เวลาเรียนทับกัน) ระบบจะเลือก
วิชาที่เจอ "อันแรก" ตามลำดับ id ในฐานข้อมูล ไม่ได้รองรับหลายห้อง/หลายกล้อง
พร้อมกันในเวอร์ชันนี้ (เหมาะกับกล้องตัวเดียว 1 ห้องเรียน ตามที่ออกแบบไว้)
"""

from datetime import datetime

from app.database import get_session
from app.models import Course, CourseSchedule

# ชื่อวันภาษาไทย ใช้แสดงผลบน Dashboard (index ตรงกับ datetime.weekday(): 0=จันทร์)
THAI_DAY_NAMES = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]


class ScheduleService:
    def __init__(self, session_factory=get_session):
        self._session_factory = session_factory

    def get_active_course(self, now: datetime = None):
        """
        หาว่า ณ เวลานี้ (now) ตรงกับคาบเรียนของวิชาไหนตามตารางเวลา
        :param now: เวลาที่จะเช็ค (ถ้าไม่ระบุ ใช้เวลาปัจจุบันของเครื่อง)
        :return: dict {"id", "course_code", "course_name"} ถ้าเจอ, None ถ้าไม่เจอ
        """
        now = now or datetime.now()
        current_day = now.weekday()  # 0=จันทร์ ... 6=อาทิตย์
        current_time = now.time()

        session = self._session_factory()
        try:
            schedules = (
                session.query(CourseSchedule)
                .filter(CourseSchedule.day_of_week == current_day)
                .all()
            )

            for schedule in schedules:
                if schedule.start_time <= current_time <= schedule.end_time:
                    course = session.query(Course).filter_by(id=schedule.course_id).first()
                    return {
                        "id": course.id,
                        "course_code": course.course_code,
                        "course_name": course.course_name,
                    }

            return None
        finally:
            session.close()

    def get_all_schedules_display(self) -> list:
        """
        คืนรายการตารางเวลาเรียนทั้งหมด แปลงเป็น string อ่านง่าย
        ใช้แสดงบน Dashboard เช่น "10301385: จันทร์ 09:00-12:00"
        """
        session = self._session_factory()
        try:
            schedules = session.query(CourseSchedule).all()
            result = []
            for schedule in schedules:
                course = session.query(Course).filter_by(id=schedule.course_id).first()
                result.append(
                    {
                        "course_code": course.course_code,
                        "course_name": course.course_name,
                        "day_name": THAI_DAY_NAMES[schedule.day_of_week],
                        "start_time": schedule.start_time.strftime("%H:%M"),
                        "end_time": schedule.end_time.strftime("%H:%M"),
                    }
                )
            return result
        finally:
            session.close()