# -*- coding: utf-8 -*-
"""
run_server.py
----------------
Entry point ของเว็บแอปทั้งระบบ รวบรวม Phase 1-4 เข้าด้วยกันแล้วรัน Flask dev server

วิธีรัน:
    python run_server.py

จากนั้นเปิดเบราว์เซอร์ไปที่:
    http://127.0.0.1:5000

กด Ctrl+C ในเทอร์มินัลเพื่อปิดเซิร์ฟเวอร์ (ระบบจะปิดกล้อง + หยุด background
monitor ให้อัตโนมัติผ่านส่วน finally ด้านล่าง)
"""

from app import create_app
from app.timeout_monitor import TimeoutMonitor

# สร้างแอปและ video_service ตอน import (ก่อนเข้า __main__)
# เพื่อให้ใช้ได้ทั้งตอนรันตรง ๆ และตอนใช้ WSGI server อื่น ๆ ในอนาคต
app, video_service = create_app()

# สำคัญ: ต้องใช้ controller ตัวเดียวกันกับที่ VideoStreamService ใช้อยู่
# (video_service.controller) ไม่ใช่สร้าง AttendanceController ใหม่ขึ้นมาลอย ๆ
# ไม่งั้นจะกลายเป็นคุยกับ session คนละตัว ข้อมูลไม่ sync กัน
monitor = TimeoutMonitor(controller=video_service.controller)


if __name__ == "__main__":
    monitor.start()
    try:
        # หมายเหตุสำคัญ:
        # - use_reloader=False: ถ้าเปิด reloader (ค่า default ตอน debug=True)
        #   Flask จะรันโปรเซสซ้ำ 2 ตัว ทำให้กล้องถูกเปิด 2 รอบพร้อมกัน (error แน่นอน)
        # - threaded=True: จำเป็นมาก เพราะ /video_feed เป็น connection ที่เปิดค้างไว้
        #   ตลอดเวลา (streaming) ถ้าไม่เปิด threaded หน้าเว็บจะค้าง ใช้ /api/* ไม่ได้เลย
        app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False, threaded=True)
    finally:
        monitor.stop()
        video_service.release()
