# -*- coding: utf-8 -*-
"""
app/report_service.py
------------------------
Phase 5: จัดการ "คาบเรียน" (ClassSession) และสร้างรายงานสรุปท้ายคาบ

แยกออกจาก AttendanceController ตามหลัก SRP:
- AttendanceController รับผิดชอบ "เปลี่ยนสถานะแบบเรียลไทม์" ระหว่างคาบเรียน
- ReportService (ไฟล์นี้) รับผิดชอบ "เริ่ม/จบคาบ" และ "สรุปผลย้อนหลัง" เป็นรายงาน

**อัปเดต (รองรับหลายวิชา):** เดิม fix วิชาเดียวผ่าน DEFAULT_COURSE_ID ตอนนี้
ใช้ ScheduleService หา "วิชาที่ Active อยู่ขณะนี้" ตามตารางเวลาเรียนแทน ตอนกด
"เริ่มคลาส" ระบบจะเช็คอัตโนมัติว่าตอนนี้ตรงกับตารางเรียนของวิชาไหน แล้วผูก
ClassSession เข้ากับวิชานั้น

หมวดหมู่ผลลัพธ์ต่อนักศึกษา 1 คน ในรายงาน:
    - "ไม่ได้ลงทะเบียนวิชานี้" -> ไม่มี Enrollment กับวิชาของคาบนี้
    - "ขาดเรียน"  -> ลงทะเบียนไว้ แต่ไม่มี AttendanceLog เลยในคาบนี้
    - "มาสาย"     -> เช็คชื่อครั้งแรกหลัง started_at เกิน LATE_THRESHOLD_MINUTES
    - "มาเรียน"   -> เช็คชื่อทันเวลา
    - คอลัมน์ "ออกนอกห้องเกินเวลา" -> จำนวนครั้งที่มี AlertLog เกิดขึ้นระหว่างคาบนี้
"""

import csv
import io
from datetime import datetime, timezone, timedelta

from app.database import get_session
from app.models import Student, Enrollment, AttendanceLog, AlertLog, ClassSession, Course
from app.config import LATE_THRESHOLD_MINUTES
from app.schedule_service import ScheduleService


class ReportService:
    """
    ตัวกลางที่ Flask routes จะคุยด้วย เพื่อเริ่ม/จบคาบเรียน
    และสร้างรายงานสรุปท้ายคาบเป็นไฟล์ CSV (เปิดด้วย Excel ได้ทันที)
    """

    def __init__(self, session_factory=get_session, schedule_service: ScheduleService = None):
        self._session_factory = session_factory
        self._schedule_service = schedule_service or ScheduleService(session_factory)

    # ======================================================================
    # จัดการคาบเรียน (Class Session)
    # ======================================================================
    def start_session(self, now: datetime = None) -> dict:
        """
        เริ่มคาบเรียนใหม่ (อาจารย์กดปุ่ม "เริ่มคลาส")
        หาวิชาที่ Active อยู่ ณ ขณะนี้จากตารางเวลาอัตโนมัติ (ไม่ต้องเลือกเอง)
        ถ้ามีคาบที่ยังไม่จบอยู่ก่อนแล้ว (วิชาเดียวกัน) จะไม่สร้างซ้ำ (ใช้คาบเดิมต่อ)
        """
        active_course = self._schedule_service.get_active_course(now)
        if active_course is None:
            return {
                "success": False,
                "message": "ไม่มีวิชาที่ตรงกับตารางเวลาเรียนในขณะนี้ ตรวจสอบตารางเวลาก่อน",
            }

        session = self._session_factory()
        try:
            active = self._get_active_session(session, active_course["id"])
            if active is not None:
                return {
                    "success": True,
                    "message": f"มีคาบเรียนวิชา {active_course['course_code']} กำลังดำเนินอยู่แล้ว ใช้คาบเดิมต่อ",
                    "started_at": active.started_at.isoformat(),
                    "course_code": active_course["course_code"],
                }

            new_session = ClassSession(course_id=active_course["id"])
            session.add(new_session)
            session.commit()
            return {
                "success": True,
                "message": f"เริ่มคาบเรียนวิชา {active_course['course_code']} ({active_course['course_name']}) แล้ว",
                "started_at": new_session.started_at.isoformat(),
                "course_code": active_course["course_code"],
            }
        finally:
            session.close()

    def end_session(self) -> dict:
        """จบคาบเรียนปัจจุบัน (อาจารย์กดปุ่ม "จบคลาส") - จบคาบล่าสุดที่ยังไม่จบ ไม่ว่าจะเป็นวิชาไหน"""
        session = self._session_factory()
        try:
            active = self._get_active_session(session)
            if active is None:
                return {"success": False, "message": "ยังไม่มีคาบเรียนที่กำลังดำเนินอยู่"}

            active.ended_at = datetime.now(timezone.utc).replace(tzinfo=None)
            session.commit()
            return {
                "success": True,
                "message": "จบคาบเรียนแล้ว ดาวน์โหลดรายงานได้ทันที",
                "ended_at": active.ended_at.isoformat(),
            }
        finally:
            session.close()

    def get_session_status(self) -> dict:
        """เช็คว่าตอนนี้มีคาบเรียนที่กำลังดำเนินอยู่หรือไม่ (ใช้ตอนโหลดหน้า Dashboard)"""
        session = self._session_factory()
        try:
            active = self._get_active_session(session)
            if active is None:
                return {"is_active": False}

            course = session.query(Course).filter_by(id=active.course_id).first()
            return {
                "is_active": True,
                "started_at": active.started_at.isoformat(),
                "course_code": course.course_code if course else "?",
            }
        finally:
            session.close()

    @staticmethod
    def _get_active_session(session, course_id: int = None):
        """คาบที่ยังไม่จบ = ended_at ยังเป็น None (ระบุ course_id ถ้าต้องการเจาะจงวิชา)"""
        query = session.query(ClassSession).filter_by(ended_at=None)
        if course_id is not None:
            query = query.filter_by(course_id=course_id)
        return query.order_by(ClassSession.started_at.desc()).first()

    @staticmethod
    def _get_latest_session(session):
        """คาบล่าสุดในระบบ ไม่ว่าจะจบแล้วหรือยังกำลังดำเนินอยู่ ไม่ว่าวิชาไหน (ใช้ตอนสร้างรายงาน)"""
        return session.query(ClassSession).order_by(ClassSession.started_at.desc()).first()

    # ======================================================================
    # สร้างรายงานสรุปท้ายคาบ
    # ======================================================================
    def generate_report_csv(self):
        """
        สร้างรายงานสรุปของคาบเรียนล่าสุด (วิชาที่ผูกกับ ClassSession นั้น)
        เป็นไฟล์ CSV (ในหน่วยความจำ ไม่เขียนลง disk)
        :return: (csv_bytes, filename)
        :raises ValueError: ถ้ายังไม่เคยมีการเริ่มคาบเรียนเลย
        """
        session = self._session_factory()
        try:
            class_session = self._get_latest_session(session)
            if class_session is None:
                raise ValueError("ยังไม่มีการเริ่มคาบเรียนเลย กรุณากดปุ่ม 'เริ่มคลาส' ก่อน")

            course_id = class_session.course_id
            course = session.query(Course).filter_by(id=course_id).first()
            session_start = class_session.started_at
            session_end = class_session.ended_at or datetime.now(timezone.utc).replace(tzinfo=None)

            # ดึงนักศึกษา "ทุกคนในระบบ" ไม่ใช่แค่คนที่ลงทะเบียนวิชานี้แล้วเท่านั้น
            # เหตุผล: ถ้ามีคนเดินผ่านกล้องแต่ไม่ได้ลงทะเบียนวิชานี้ (เช่น ลงทะเบียน
            # วิชาอื่น หรือยังไม่ได้ลงทะเบียนเลย) อาจารย์ควรเห็นชื่อคนนั้นในรายงาน
            # ด้วย พร้อมสถานะที่บอกชัดว่า "ไม่ได้ลงทะเบียนวิชานี้"
            students = session.query(Student).all()

            rows = [
                [
                    "รหัสนักศึกษา",
                    "ชื่อ-นามสกุล",
                    "สถานะ",
                    "เวลาเข้าเรียน",
                    "ออกนอกห้องเกินเวลา (ครั้ง)",
                ]
            ]

            for student in students:
                is_enrolled = (
                    session.query(Enrollment)
                    .filter_by(student_id=student.id, course_id=course_id)
                    .first()
                    is not None
                )

                alert_count = (
                    session.query(AlertLog)
                    .filter(
                        AlertLog.student_id == student.id,
                        AlertLog.triggered_at >= session_start,
                        AlertLog.triggered_at <= session_end,
                    )
                    .count()
                )

                if not is_enrolled:
                    status = "ไม่ได้ลงทะเบียนวิชานี้"
                    check_in_str = "-"
                else:
                    attendance_log = (
                        session.query(AttendanceLog)
                        .filter(
                            AttendanceLog.student_id == student.id,
                            AttendanceLog.course_id == course_id,
                            AttendanceLog.check_in_time >= session_start,
                            AttendanceLog.check_in_time <= session_end,
                        )
                        .order_by(AttendanceLog.check_in_time.asc())
                        .first()
                    )

                    if attendance_log is None:
                        status = "ขาดเรียน"
                        check_in_str = "-"
                    else:
                        late_cutoff = session_start + timedelta(minutes=LATE_THRESHOLD_MINUTES)
                        status = "มาสาย" if attendance_log.check_in_time > late_cutoff else "มาเรียน"
                        check_in_str = attendance_log.check_in_time.strftime("%H:%M:%S")

                rows.append(
                    [
                        student.student_code,
                        student.full_name,
                        status,
                        check_in_str,
                        str(alert_count),
                    ]
                )

            output = io.StringIO()
            writer = csv.writer(output)
            # แถวแรกพิเศษ: ระบุว่ารายงานนี้เป็นของวิชาไหน คาบไหน (ช่วยตอนมีหลายวิชา)
            writer.writerow([f"รายงานวิชา {course.course_code} ({course.course_name})"])
            writer.writerow([f"เริ่มคาบ: {session_start.strftime('%Y-%m-%d %H:%M:%S')}  ถึง  {session_end.strftime('%H:%M:%S')}"])
            writer.writerow([])
            writer.writerows(rows)

            # ใช้ utf-8-sig (มี BOM) เพื่อให้ Excel บน Windows เปิดไฟล์แล้วอ่านภาษาไทย
            # ได้ถูกต้อง (ถ้าใช้ utf-8 ธรรมดา Excel มักจะอ่านภาษาไทยเพี้ยนเป็นตัวอักษรมั่วๆ)
            csv_bytes = output.getvalue().encode("utf-8-sig")

            date_str = session_start.strftime("%Y%m%d_%H%M")
            filename = f"attendance_report_{course.course_code}_{date_str}.csv"

            return csv_bytes, filename
        finally:
            session.close()
