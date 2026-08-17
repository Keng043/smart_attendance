# -*- coding: utf-8 -*-
"""
app/video_stream.py
----------------------
คลาสนี้ "ประกอบ" (compose) ส่วนต่างๆ จาก Phase ก่อนหน้าเข้าด้วยกัน:
- CameraStream (Phase 2)         -> อ่านภาพจากกล้อง
- FaceRecognizer (Phase 2)        -> ระบุตัวตนใบหน้าในภาพ
- AttendanceController (Phase 3) -> ตัดสินใจเปลี่ยนสถานะแบบอัตโนมัติ

**อัปเดต: เปลี่ยนเป็นระบบอัตโนมัติเต็มรูปแบบ (Fully Automatic, Single Camera)**
ไม่มีการสลับโหมดกล้องด้วยปุ่มอีกต่อไป กล้องตัวเดียวจับที่ประตูห้องเรียน
ทุกครั้งที่จำหน้านักศึกษาได้ ระบบจะเรียก controller.handle_face_detected()
แล้วให้ AttendanceController ตัดสินใจเองว่าควรตีความเป็น "เข้า" หรือ "ออก"
จากสถานะปัจจุบันของนักศึกษาคนนั้น (ดูรายละเอียดที่ attendance_controller.py)

Debounce Logic (สำคัญมาก):
ถ้าไม่มีการหน่วงเวลา นักศึกษาที่เดินผ่านหรือยืนหน้ากล้องนิ่งๆ จะถูกเรียก
handle_face_detected() ทุกเฟรม (~30 ครั้ง/วินาที) ทำให้ระบบตีความว่า
"เข้า-ออก-เข้า-ออก" สลับกันไม่หยุดภายในไม่กี่วินาที จึงต้องมี cooldown
ต่อคน (CHECKPOINT_COOLDOWN_SECONDS) ก่อนจะยอมให้ trigger event ซ้ำสำหรับ
คนเดิมได้อีกครั้ง ค่านี้ควรตั้งให้นานพอที่คนจะ "เดินผ่านกล้องจนสุด" ได้
(ค่าเริ่มต้น 8 วินาที ปรับได้ที่ app/config.py)
"""

import time

import cv2

from app.camera import CameraStream
from app.face_recognition_service import FaceEncodingRepository, FaceRecognizer
from app.attendance_controller import AttendanceController
from app.database import get_session
from app.models import Student, StudentState
from app.config import CHECKPOINT_COOLDOWN_SECONDS, CAMERA_SOURCE


class VideoStreamService:
    """
    ตัวกลางเดียวที่ Flask routes (Phase 4) จะคุยด้วย เพื่อขอภาพสตรีม (generate_frames)
    ไม่มีการสลับโหมดใดๆ แล้ว ทำงานอัตโนมัติทั้งหมด
    """

    def __init__(self):
        self._camera = CameraStream(source=CAMERA_SOURCE)
        self._repository = FaceEncodingRepository()
        self._recognizer: FaceRecognizer | None = None

        # เปิดเผย controller ออกมาเป็น public attribute เพราะ TimeoutMonitor
        # (Phase 3) ต้องใช้ controller ตัวเดียวกันนี้ ไม่งั้นจะมีสอง session แยกกัน
        self.controller = AttendanceController()

        # เก็บเวลาที่ trigger event ล่าสุดของนักศึกษาแต่ละคน (สำหรับ debounce)
        self._last_triggered_at: dict[int, float] = {}

        self._is_running = False

    # ======================================================================
    # Lifecycle: เปิด/ปิด กล้องและโหลดข้อมูลใบหน้า
    # ======================================================================
    def initialize(self):
        """โหลดใบหน้าต้นแบบ + เปิดกล้อง (เรียกครั้งเดียวตอนแอปเริ่มทำงาน)"""
        print("[VIDEO] กำลังโหลดใบหน้าต้นแบบจากฐานข้อมูล ...")
        self._repository.load_known_faces()
        self._recognizer = FaceRecognizer(self._repository, tolerance=0.5)

        print("[VIDEO] กำลังเปิดกล้อง ...")
        self._camera.start()
        self._is_running = True

    def release(self):
        """ปิดกล้องอย่างปลอดภัย (เรียกตอนแอปกำลังจะปิด เพื่อไม่ให้กล้องค้าง)"""
        self._is_running = False
        self._camera.release()

    # ======================================================================
    # Core: สร้างสตรีมวิดีโอ (Generator ที่ Flask ดึงไปใช้)
    # ======================================================================
    def generate_frames(self):
        """
        แต่ละรอบของลูป:
        1. อ่านภาพจากกล้อง
        2. ตรวจจับ + ระบุตัวตนใบหน้า (Phase 2)
        3. ถ้าเจอนักศึกษาที่รู้จัก และผ่าน cooldown แล้ว -> เรียก Business Logic
           แบบอัตโนมัติ (ไม่ต้องระบุโหมดใดๆ)
        4. วาดกรอบ + ชื่อ + สถานะปัจจุบัน ทับบนภาพ
        5. เข้ารหัสเป็น JPEG แล้ว yield ออกไปตามฟอร์แมต multipart ที่เบราว์เซอร์เข้าใจ
        """
        while self._is_running:
            frame = self._camera.read_frame()
            if frame is None:
                continue

            faces = self._recognizer.identify_faces_in_frame(frame)

            for face in faces:
                student_id = face["student_id"]
                if student_id is not None:
                    name, state_label = self._get_student_display_info(student_id)
                    color = (0, 200, 0)  # เขียว = จำได้
                    self._trigger_detection_if_allowed(student_id)
                else:
                    name, state_label = "Unknown", ""
                    color = (0, 0, 255)  # แดง = จำไม่ได้

                label = f"{name} {state_label}".strip()
                self._draw_face_box(frame, face["location"], label, color)

            self._draw_banner(frame)

            success, buffer = cv2.imencode(".jpg", frame)
            if not success:
                continue

            frame_bytes = buffer.tobytes()
            # รูปแบบ multipart/x-mixed-replace ที่เบราว์เซอร์ต้องการ สำหรับแสดงวิดีโอสตรีม
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )

    def _trigger_detection_if_allowed(self, student_id: int):
        """เช็ค cooldown ก่อนเรียก Business Logic เพื่อกันการ trigger รัวๆทุกเฟรม"""
        now = time.time()
        last_time = self._last_triggered_at.get(student_id, 0)

        if now - last_time >= CHECKPOINT_COOLDOWN_SECONDS:
            self._last_triggered_at[student_id] = now
            result = self.controller.handle_face_detected(student_id)
            print(f"[VIDEO] {result['message']}")

    # ======================================================================
    # Helper Methods: วาดภาพ / ดึงชื่อ+สถานะนักศึกษา
    # ======================================================================
    @staticmethod
    def _get_student_display_info(student_id: int):
        """คืนค่า (ชื่อ, สถานะปัจจุบันในวงเล็บ) เช่น ('Kongkiat Somchai', '(In_Class)')"""
        session = get_session()
        try:
            student = session.query(Student).filter_by(id=student_id).first()
            if student is None:
                return "Unknown", ""

            state = session.query(StudentState).filter_by(student_id=student_id).first()
            state_label = f"({state.current_state.value})" if state else ""
            return student.full_name, state_label
        finally:
            session.close()

    @staticmethod
    def _draw_face_box(frame, location, label, color):
        top, right, bottom, left = location
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.rectangle(frame, (left, bottom), (right, bottom + 30), color, cv2.FILLED)
        cv2.putText(
            frame, label, (left + 6, bottom + 22),
            cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1,
        )

    @staticmethod
    def _draw_banner(frame):
        """แถบด้านบนบอกว่าระบบทำงานอัตโนมัติ (ไม่มีปุ่มสลับโหมดแล้ว)"""
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 34), (50, 50, 50), cv2.FILLED)
        cv2.putText(
            frame, "AUTO DETECT MODE - Single Camera",
            (10, 24), cv2.FONT_HERSHEY_DUPLEX, 0.65, (255, 255, 255), 1,
        )