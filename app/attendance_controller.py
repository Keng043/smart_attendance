# -*- coding: utf-8 -*-
"""
app/attendance_controller.py
-------------------------------
คลาสนี้คือ "สมอง" ของ Business Logic ทั้งหมดในระบบ (Phase 3 -> ปรับปรุงเป็น
"Fully Automatic Single-Camera Mode" ตามที่ผู้ใช้ต้องการ)

เปลี่ยนจากเดิมที่ต้องกดปุ่มสลับโหมดกล้อง (หน้าประตู vs ห้องน้ำ) มาเป็น
"กล้องเดียวจับที่ประตูห้องเรียน" แล้วให้ระบบตัดสินใจเองโดยอัตโนมัติว่า
การที่เจอหน้านักศึกษาคนนี้ ควรตีความว่า "เดินเข้า" หรือ "เดินออก"
โดยดูจาก "สถานะปัจจุบัน" ของนักศึกษาคนนั้นเป็นหลัก (Toggle Logic):

    สถานะปัจจุบัน = Missing (ยังไม่เคยเช็ค หรือเกินเวลาไปแล้ว)
        -> ตีความว่า "เดินเข้าห้อง"  -> เปลี่ยนเป็น In_Class

    สถานะปัจจุบัน = In_Class (อยู่ในห้องอยู่แล้ว)
        -> ตีความว่า "เดินออกจากห้อง" -> เปลี่ยนเป็น Away (เริ่มจับเวลา)

    สถานะปัจจุบัน = Away (ออกไปแล้ว ยังไม่เกินเวลา)
        -> ตีความว่า "เดินกลับเข้าห้อง" -> เปลี่ยนเป็น In_Class

ข้อดี: ไม่ต้องมี UI ปุ่มกดใดๆ ตั้งกล้องไว้ตัวเดียวที่ประตู ระบบทำงานอัตโนมัติ 100%
ข้อจำกัดที่ควรรู้ (สำคัญ อธิบายให้ผู้ใช้ทราบตอนพรีเซนต์ได้):
    เพราะใช้กล้องตัวเดียว ระบบ "ไม่รู้ทิศทางการเดิน" จริงๆ จึงอนุมานจากสถานะ
    ก่อนหน้าเท่านั้น ถ้านักศึกษาเดินผ่านกล้อง 2 ครั้งติดกันเร็วมาก (เช่นเดินเข้า
    แล้วเดินย้อนกลับทันที) ระบบจะตีความสลับ เข้า/ออก ผิดพลาดได้ จึงต้องมี
    Debounce (CHECKPOINT_COOLDOWN_SECONDS ใน video_stream.py) ช่วยกันไว้ระดับหนึ่ง

แยกออกจาก Facial Recognition (Phase 2) และ Database Models (Phase 1) โดยสิ้นเชิง
ตามหลัก SRP เหมือนเดิม การออกแบบนี้ทำให้เทส Business Logic ได้โดยไม่ต้องเปิด
กล้องจริงเลย (ดูตัวอย่างที่ demo_business_logic.py)
"""

from datetime import datetime, timezone, timedelta

from app.database import get_session
from app.models import (
    Student,
    Enrollment,
    AttendanceLog,
    StudentState,
    StateEnum,
    AlertLog,
)
from app.config import AWAY_TIMEOUT_SECONDS
from app.schedule_service import ScheduleService


class AttendanceController:
    """
    ตัวควบคุมหลักของ Business Logic แบบอัตโนมัติ (Single Camera, No Manual Mode)

    - handle_face_detected(): จุดเข้าเดียวที่ Phase 4 (video_stream.py) จะเรียกใช้
      ทุกครั้งที่ Facial Recognition จำนักศึกษาได้จากกล้อง (ตัวเดียว)
    - check_and_flag_missing_students(): ตรวจสอบว่ามีใครหายไปนานเกินกำหนดหรือยัง
      ถูกเรียกเป็นระยะๆ จาก TimeoutMonitor (background thread) เหมือนเดิม ไม่เปลี่ยน

    **อัปเดต (รองรับหลายวิชา):** เดิมระบบ fix วิชาเดียวผ่าน DEFAULT_COURSE_ID
    ตอนนี้เปลี่ยนมาถาม ScheduleService ว่า "ขณะนี้เป็นคาบเรียนของวิชาไหน"
    ตามตารางเวลาที่ตั้งไว้ (CourseSchedule) แทน เพื่อให้กล้องตัวเดียวใช้ตรวจจับ
    ได้หลายวิชาที่ใช้ห้องเดียวกันคนละช่วงเวลา (เช่น 10301385 กับ 1030199)
    """

    def __init__(self, session_factory=get_session, schedule_service: ScheduleService = None):
        # Dependency Injection: รับ session_factory เข้ามา เพื่อสลับ DB หรือ mock ตอนเทสได้ง่าย
        self._session_factory = session_factory
        self._schedule_service = schedule_service or ScheduleService(session_factory)

    # ======================================================================
    # จุดเข้าหลัก (จุดเดียว): กล้องหน้าประตูจับใบหน้านักศึกษาได้ 1 คน
    # ======================================================================
    def handle_face_detected(self, student_id: int, now: datetime = None) -> dict:
        """
        :param student_id: id ของนักศึกษาที่ Facial Recognition จำได้ (จาก Phase 2)
        :param now: เวลาที่จะใช้เช็คตารางเรียน (ไม่ระบุ = ใช้เวลาปัจจุบันของเครื่อง)
                    เปิดให้ระบุได้เพื่อความสะดวกตอนเขียนเทส (ดู demo_business_logic.py)
        :return: dict สรุปผลลัพธ์ เช่น {"success": True, "message": "..."}
        """
        active_course = self._schedule_service.get_active_course(now)
        if active_course is None:
            return {
                "success": False,
                "message": "ไม่มีวิชาที่กำลังเรียนอยู่ตามตารางเวลาในขณะนี้",
            }

        session = self._session_factory()
        try:
            student = session.query(Student).filter_by(id=student_id).first()
            if student is None:
                return {"success": False, "message": "ไม่พบนักศึกษาคนนี้ในระบบ"}

            state = self._get_or_create_state(session, student_id)

            if state.current_state == StateEnum.IN_CLASS:
                # อยู่ในห้องอยู่แล้ว เจอหน้าอีกครั้ง -> ตีความว่ากำลังเดินออก
                return self._mark_as_leaving(session, student, state)
            else:
                # สถานะเป็น Missing/Not_Arrived (ยังไม่เคยเข้า/เกินเวลาไปแล้ว) หรือ Away
                # (ยังไม่เกินเวลา) ทั้งหมดนี้ เจอหน้า = ตีความว่ากำลังเดินเข้าห้อง
                return self._mark_as_entering(session, student, state, active_course["id"])
        finally:
            session.close()

    # ----------------------------------------------------------------------
    # Logic: เดินเข้าห้อง (ครั้งแรก = เช็คชื่อ, ครั้งต่อไป = กลับเข้าห้อง)
    # ----------------------------------------------------------------------
    def _mark_as_entering(self, session, student, state, course_id: int) -> dict:
        # เช็คสิทธิ์ก่อน: นักศึกษาคนนี้ลงทะเบียนวิชาที่กำลังเรียนอยู่ขณะนี้ไว้หรือไม่
        is_enrolled = (
            session.query(Enrollment)
            .filter_by(student_id=student.id, course_id=course_id)
            .first()
            is not None
        )
        if not is_enrolled:
            return {
                "success": False,
                "message": f"{student.full_name} ไม่มีสิทธิ์เข้าเรียนวิชานี้ (ไม่ได้ลงทะเบียน)",
            }

        # เช็คว่านี่คือ "การเข้าเรียนครั้งแรก" ของนักศึกษาคนนี้ในวิชานี้หรือไม่
        # (ยังไม่มี AttendanceLog เลยในวิชานี้) ถ้าเป็นครั้งแรก -> สร้างประวัติเช็คชื่อ
        # ถ้าเคยเช็คชื่อไปแล้ว (แค่กลับมาจาก Away/Missing) -> ไม่สร้างซ้ำ
        already_checked_in_before = (
            session.query(AttendanceLog)
            .filter_by(student_id=student.id, course_id=course_id)
            .first()
            is not None
        )
        was_missing = state.current_state == StateEnum.MISSING

        if not already_checked_in_before:
            session.add(
                AttendanceLog(
                    student_id=student.id,
                    course_id=course_id,
                    check_in_time=datetime.now(timezone.utc).replace(tzinfo=None),
                    status="Present",
                )
            )

        state.current_state = StateEnum.IN_CLASS
        state.state_changed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.commit()

        if not already_checked_in_before:
            return {"success": True, "message": f"เช็คชื่อเข้าเรียนสำเร็จ: {student.full_name}"}
        elif was_missing:
            return {
                "success": True,
                "message": f"{student.full_name} กลับเข้าห้องแล้ว (เกินเวลาไปแล้ว แต่ยกเลิกแจ้งเตือนแล้ว)",
            }
        else:
            return {"success": True, "message": f"{student.full_name} กลับเข้าห้องแล้ว"}

    # ----------------------------------------------------------------------
    # Logic: เดินออกจากห้อง (เริ่มจับเวลา)
    # ----------------------------------------------------------------------
    def _mark_as_leaving(self, session, student, state) -> dict:
        state.current_state = StateEnum.AWAY
        state.state_changed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.commit()
        return {"success": True, "message": f"{student.full_name} เดินออกจากห้อง (เริ่มจับเวลา)"}

    # ======================================================================
    # ตรวจสอบ Timer: ใครออกไปนานเกินกำหนดหรือยัง (ไม่เปลี่ยนจาก Phase 3 เดิม)
    # ======================================================================
    def check_and_flag_missing_students(self) -> list:
        """
        ไล่ตรวจสอบนักศึกษาทุกคนที่สถานะเป็น Away อยู่ ว่าเกินเวลาที่กำหนด
        (AWAY_TIMEOUT_SECONDS จาก config.py) หรือยัง ถ้าเกิน จะเปลี่ยนสถานะเป็น Missing

        ควรเรียกฟังก์ชันนี้เป็นระยะๆ (เช่นทุก 1-2 วินาที) จาก background thread
        (ดู TimeoutMonitor ใน app/timeout_monitor.py)

        :return: list ของชื่อนักศึกษาที่ "เพิ่งถูกตีสถานะ Missing" ในการเช็ครอบนี้
        """
        session = self._session_factory()
        newly_missing_names = []
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            threshold = timedelta(seconds=AWAY_TIMEOUT_SECONDS)

            away_states = (
                session.query(StudentState).filter_by(current_state=StateEnum.AWAY).all()
            )

            for state in away_states:
                elapsed = now - state.state_changed_at
                if elapsed >= threshold:
                    state.current_state = StateEnum.MISSING
                    # ตั้งใจไม่อัปเดต state_changed_at ตรงนี้ เพื่อเก็บไว้ว่า
                    # "หายไปตั้งแต่เมื่อไหร่" สำหรับ Dashboard ใน Phase 5

                    # บันทึกลง AlertLog ไว้เป็นประวัติ (ไม่ทับกับ StudentState)
                    # เพื่อให้ตอนสร้างรายงานท้ายคาบ รู้ว่านักศึกษาคนนี้เคยหายไป
                    # เกินเวลาช่วงไหนบ้าง ถึงแม้ตอนจบคาบจะกลับเข้าห้องมาแล้วก็ตาม
                    session.add(AlertLog(student_id=state.student_id, triggered_at=now))

                    newly_missing_names.append(state.student.full_name)

            if newly_missing_names:
                session.commit()

            return newly_missing_names
        finally:
            session.close()

    # ----------------------------------------------------------------------
    # Helper: ดึงสถานะปัจจุบันของนักศึกษา ถ้ายังไม่มีให้สร้างใหม่ (default = Missing)
    # ----------------------------------------------------------------------
    @staticmethod
    def _get_or_create_state(session, student_id: int) -> StudentState:
        state = session.query(StudentState).filter_by(student_id=student_id).first()
        if state is None:
            # หมายเหตุ: จุดนี้ปกติจะไม่ถูกเรียกตอนสถานะเป็น "ยังไม่มาเรียน" อยู่แล้ว
            # เพราะ handle_face_detected() ถูกเรียกก็ต่อเมื่อ "เจอหน้า" แล้วเท่านั้น
            # (ตอนยังไม่มาเรียนจะไม่มีแถว StudentState เลย ดู routes.py /api/status
            # ที่ fallback เป็น "Not_Arrived" ให้ตอนไม่มีแถว) แต่ตั้งค่าเริ่มต้นไว้ให้
            # ถูกต้องเผื่อกรณีอื่นเรียกใช้ฟังก์ชันนี้ในอนาคต
            state = StudentState(
                student_id=student_id,
                current_state=StateEnum.NOT_ARRIVED,
                state_changed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            session.add(state)
            session.flush()  # flush เพื่อให้ state.id ถูกสร้างขึ้นก่อนนำไปใช้ต่อ
        return state
