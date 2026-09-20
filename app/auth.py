# -*- coding: utf-8 -*-
"""
app/auth.py
-------------
ระบบยืนยันตัวตนแบบง่าย (Session-based Authentication) สำหรับอาจารย์
ก่อนเข้าดู Dashboard หรือ Export รายงาน ต้อง Login ก่อนเสมอ

ใช้ Flask session (cookie-based) เก็บแค่ instructor_id หลัง login สำเร็จ
ไม่เก็บรหัสผ่านไว้ใน session เด็ดขาด (เก็บแค่ password_hash ใน DB เท่านั้น
ผ่าน werkzeug.security ซึ่งติดมากับ Flask อยู่แล้ว ไม่ต้องลง library เพิ่ม)

มี Decorator 2 แบบ เพราะพฤติกรรมที่ควรทำตอนยังไม่ login ต่างกัน:
- login_required    -> สำหรับหน้าเว็บ (เช่น /dashboard) ถ้ายังไม่ login ให้ redirect ไปหน้า /login
- api_login_required -> สำหรับ API endpoint (เช่น /api/report/export) ถ้ายังไม่ login
                         ให้ตอบ JSON 401 กลับไป (เพราะเป็น AJAX call, redirect ไม่มีประโยชน์)
"""

from functools import wraps

from flask import session, redirect, url_for, request, jsonify

from app.database import get_session
from app.models import Instructor


def login_required(view_func):
    """ใช้ครอบ route ที่เป็นหน้าเว็บ (HTML) - ยังไม่ login จะถูก redirect ไปหน้า /login"""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("instructor_id"):
            return redirect(url_for("main.login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapped


def role_required(*allowed_roles):
    """Require an authenticated instructor with one of the allowed roles."""
    normalized = {role.upper() for role in allowed_roles}

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            instructor_id = session.get("instructor_id")
            if not instructor_id:
                return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบก่อน"}), 401

            db = get_session()
            try:
                instructor = db.query(Instructor).filter_by(id=instructor_id).first()
                if instructor is None or (instructor.role or "INSTRUCTOR").upper() not in normalized:
                    return jsonify({"success": False, "message": "ไม่มีสิทธิ์เข้าถึงข้อมูลนี้"}), 403
            finally:
                db.close()
            return view_func(*args, **kwargs)

        return wrapped
    return decorator


def api_login_required(view_func):
    """ใช้ครอบ API endpoint (JSON) - ยังไม่ login จะได้ HTTP 401 กลับไปเป็น JSON"""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("instructor_id"):
            return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบก่อน"}), 401
        return view_func(*args, **kwargs)

    return wrapped