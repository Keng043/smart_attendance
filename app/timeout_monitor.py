# -*- coding: utf-8 -*-
"""
app/timeout_monitor.py
-------------------------
คลาสนี้ทำหน้าที่ "จับเวลาเบื้องหลัง" (Background Timer)
คอยเรียก AttendanceController.check_and_flag_missing_students() เป็นระยะ ๆ
เพื่อตรวจสอบว่ามีนักศึกษาคนไหนไปห้องน้ำนานเกินกำหนดหรือยัง

ทำงานแบบ background thread (daemon) เพื่อไม่ให้บล็อกการทำงานหลักของโปรแกรม
เช่นตอนเอาไปรวมกับเว็บ Flask ใน Phase 4 เว็บจะยังตอบสนองได้ปกติ
โดยมี thread นี้แอบตรวจสอบสถานะอยู่เบื้องหลังตลอดเวลา

แยกออกจาก AttendanceController ตามหลัก SRP:
- AttendanceController รับผิดชอบ "กฎ" ว่าเมื่อไหร่ควรเปลี่ยนสถานะ
- TimeoutMonitor รับผิดชอบแค่ "เรียกเช็คซ้ำ ๆ ตามรอบเวลา" เท่านั้น
"""

import threading

from app.attendance_controller import AttendanceController
from app.config import MONITOR_POLL_INTERVAL_SECONDS


class TimeoutMonitor:
    """
    ใช้งานตัวอย่าง:
        monitor = TimeoutMonitor(on_missing_callback=lambda name: print(f"แจ้งเตือน: {name}"))
        monitor.start()
        ...
        monitor.stop()
    """

    def __init__(
        self,
        controller: AttendanceController = None,
        poll_interval: int = None,
        on_missing_callback=None,
    ):
        # ถ้าไม่ส่ง controller มา จะสร้างตัวใหม่ให้เอง (สะดวกตอนใช้งานง่าย ๆ)
        self._controller = controller or AttendanceController()
        self._poll_interval = poll_interval or MONITOR_POLL_INTERVAL_SECONDS

        # callback ที่จะถูกเรียกทุกครั้งที่มีคนถูกตีสถานะ Missing ใหม่
        # เช่นจะเอาไปส่งแจ้งเตือนขึ้นหน้าเว็บ Dashboard ใน Phase 5 ก็ทำผ่านตรงนี้ได้
        self._on_missing_callback = on_missing_callback

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self):
        """เริ่มรัน background thread คอยเช็คสถานะทุก ๆ poll_interval วินาที"""
        if self._thread is not None:
            print("[MONITOR] กำลังทำงานอยู่แล้ว ไม่ต้อง start ซ้ำ")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"[MONITOR] เริ่มตรวจสอบสถานะ Away ทุก {self._poll_interval} วินาที")

    def stop(self):
        """สั่งหยุด background thread อย่างปลอดภัย"""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        print("[MONITOR] หยุดการตรวจสอบแล้ว")

    def _run_loop(self):
        """ลูปหลักที่รันอยู่เบื้องหลัง วนเช็คสถานะทุก ๆ poll_interval วินาที"""
        while not self._stop_event.is_set():
            newly_missing = self._controller.check_and_flag_missing_students()

            for student_name in newly_missing:
                print(f"[ALERT] {student_name} หายไปนานเกินกำหนด! แจ้งเตือนอาจารย์")
                if self._on_missing_callback:
                    self._on_missing_callback(student_name)

            # wait() คืนค่าเร็วกว่ากำหนดได้ทันทีถ้ามีคนเรียก stop() ระหว่างรอ
            # ต่างจาก time.sleep() ตรงที่ stop() จะไม่ต้องรอครบรอบก่อนถึงจะหยุดจริง
            self._stop_event.wait(self._poll_interval)
