# -*- coding: utf-8 -*-
"""
app/__init__.py
----------------
Application Factory ของ Flask (Phase 4)

หน้าที่ของไฟล์นี้คือ "ประกอบ" (compose) ส่วนต่าง ๆ ของแอปเข้าด้วยกัน:
- สร้าง Flask app
- สร้าง VideoStreamService (Phase 4) แล้วเก็บไว้ใน app.config เพื่อให้
  routes.py เข้าถึงได้ผ่าน current_app.config["VIDEO_SERVICE"]
- ลงทะเบียน Blueprint ของ routes ทั้งหมด

ทำไมต้องใช้ Pattern "Application Factory" (ฟังก์ชัน create_app แทนสร้าง
app แบบ global ตรง ๆ)?
เพราะแยกการ "สร้างแอป" ออกจากการ "รันแอป" (ทำใน run_server.py)
ทำให้เทสแอปได้ง่ายขึ้นในอนาคต (สร้างหลาย instance สำหรับเทสแต่ละเคสได้)
"""

import os

from flask import Flask

from app.video_stream import VideoStreamService
from app.report_service import ReportService


def create_app():
    """
    สร้างและตั้งค่า Flask app ให้พร้อมใช้งาน
    :return: (app, video_service) - คืนทั้งแอปและ video_service ออกไปด้วย
             เพราะ run_server.py ต้องใช้ video_service ไปสร้าง TimeoutMonitor
             (ต้องใช้ AttendanceController ตัวเดียวกัน ไม่งั้นจะมีสอง session แยกกัน)
    """
    app = Flask(__name__)

    # secret_key จำเป็นสำหรับ Flask session (ใช้เข้ารหัส/ยืนยัน session cookie)
    # ใช้ os.urandom() สุ่มใหม่ทุกครั้งที่รัน server ก็เพียงพอสำหรับงานนี้
    # (ผลคือถ้า restart server ทุกคนจะต้อง login ใหม่ ซึ่งรับได้สำหรับระบบนี้)
    app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

    video_service = VideoStreamService()
    video_service.initialize()
    app.config["VIDEO_SERVICE"] = video_service

    # ReportService ไม่ต้องพึ่งกล้อง/dlib เลย จึงสร้างง่ายๆ ตรงนี้ได้ทันที
    app.config["REPORT_SERVICE"] = ReportService()

    from app.routes import bp as main_blueprint
    app.register_blueprint(main_blueprint)

    return app, video_service