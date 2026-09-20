# -*- coding: utf-8 -*-
"""
app/routes.py
---------------
กำหนด HTTP Routes ทั้งหมดของระบบ แยกออกจาก app/__init__.py (Application Factory)
ตามหลัก SRP: __init__.py มีหน้าที่แค่ "ประกอบ/ตั้งค่าแอป" ส่วนไฟล์นี้มีหน้าที่
"นิยามว่า URL ไหนทำอะไร" เท่านั้น

Endpoints:
    GET  /                       -> หน้าเว็บกล้อง (วิดีโอสตรีมอัตโนมัติ, สาธารณะ ไม่ต้อง login)
    GET  /video_feed              -> สตรีมวิดีโอ MJPEG จากกล้อง (สาธารณะ)
    GET  /login                   -> หน้า Login สำหรับอาจารย์
    POST /login                   -> ตรวจสอบ username/password
    GET  /logout                  -> ออกจากระบบ

    ต้อง Login ก่อนเข้าถึงทั้งหมดด้านล่างนี้ (ข้อมูลนักศึกษา/รายงาน):
    GET  /dashboard                -> หน้า Dashboard ของอาจารย์
    GET  /api/status                 -> สถานะปัจจุบันของนักศึกษาทุกคน
    GET  /api/alerts                 -> รายชื่อนักศึกษาที่สถานะเป็น Missing อยู่ตอนนี้
    GET  /api/session/status          -> เช็คว่ามีคาบเรียนที่กำลังดำเนินอยู่หรือไม่
    POST /api/session/start           -> อาจารย์กดปุ่ม "เริ่มคลาส"
    POST /api/session/end             -> อาจารย์กดปุ่ม "จบคลาส"
    GET  /api/report/export           -> ดาวน์โหลดรายงานสรุปท้ายคาบเป็น CSV
"""

from flask import Blueprint, Response, render_template, jsonify, current_app, request, session as flask_session, redirect, url_for
from werkzeug.security import check_password_hash

from app.database import get_session
from app.models import Student, StudentState, StateEnum, Instructor
from app.auth import login_required, api_login_required
from app.audit import record_event
from app.csrf import csrf_protect
from app.validation import validate_login_input

bp = Blueprint("main", __name__)


# ==========================================================================
# หน้าเว็บกล้อง (สาธารณะ - ไม่ต้อง login เพราะเป็นแค่จอแสดงกล้องในห้องเรียน
# ไม่ได้เปิดเผยข้อมูลนักศึกษารายบุคคลใดๆ)
# ==========================================================================
@bp.route("/")
def index():
    """หน้าเว็บกล้อง แสดงวิดีโอสตรีมแบบอัตโนมัติ"""
    return render_template("index.html")


@bp.route("/video_feed")
def video_feed():
    """
    เส้นสตรีมวิดีโอ ใช้ mimetype แบบ multipart/x-mixed-replace
    ซึ่งเป็นมาตรฐานที่เบราว์เซอร์รู้จักสำหรับแสดงภาพต่อเนื่องแบบ MJPEG
    """
    video_service = current_app.config["VIDEO_SERVICE"]
    return Response(
        video_service.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


# ==========================================================================
# ระบบ Login สำหรับอาจารย์
# ==========================================================================
@bp.route("/login", methods=["GET", "POST"])
@csrf_protect
def login():
    """
    หน้า Login ของอาจารย์ - ต้องกรอก username/password ให้ตรงกับที่มีใน
    ตาราง Instructor ก่อน จึงจะเข้าดู Dashboard/รายงานได้
    """
    if request.method == "GET":
        return render_template("login.html", error=None)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    validation_error = validate_login_input(username, password)
    if validation_error:
        return render_template("login.html", error=validation_error), 400

    session = get_session()
    try:
        instructor = session.query(Instructor).filter_by(username=username).first()

        if instructor is None or not check_password_hash(instructor.password_hash, password):
            return render_template("login.html", error="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

        # เก็บแค่ instructor_id ไว้ใน session cookie เท่านั้น (ไม่เก็บรหัสผ่าน)
        flask_session["instructor_id"] = instructor.id
        flask_session["instructor_name"] = instructor.full_name or instructor.username
        record_event(session, "USER_LOGIN", instructor.id)
        session.commit()

        next_url = request.args.get("next")
        # ป้องกัน open redirect: อนุญาตเฉพาะ path ภายในแอป
        if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
            next_url = url_for("main.dashboard")
        return redirect(next_url)
    finally:
        session.close()


@bp.route("/logout", methods=["POST"])
@csrf_protect
def logout():
    """ออกจากระบบ - บันทึก audit event แล้วล้าง session"""
    instructor_id = flask_session.get("instructor_id")
    session = get_session()
    try:
        if instructor_id:
            record_event(session, "USER_LOGOUT", instructor_id)
            session.commit()
    finally:
        session.close()
    flask_session.clear()
    return redirect(url_for("main.login"))


# ==========================================================================
# ต้อง Login ก่อนเข้าถึงทั้งหมดด้านล่างนี้ (ข้อมูลนักศึกษา + รายงาน)
# ==========================================================================
@bp.route("/dashboard")
@login_required
def dashboard():
    """หน้า Dashboard ของอาจารย์ - ดูสถานะสด + เริ่ม/จบคาบ + export รายงาน"""
    return render_template("dashboard.html", instructor_name=flask_session.get("instructor_name"))


@bp.route("/api/status")
@api_login_required
def get_status():
    """คืนสถานะปัจจุบันของนักศึกษาทุกคนในระบบ เป็น JSON (Dashboard poll endpoint นี้เป็นระยะๆ)"""
    session = get_session()
    try:
        students = session.query(Student).all()
        result = []
        for student in students:
            state = student.state
            if state is None:
                # ไม่มีแถว StudentState เลย = ยังไม่เคยเดินผ่านกล้องเลยตั้งแต่เริ่มระบบ
                current_state_value = "Not_Arrived"
                state_changed_at_value = None
            else:
                current_state_value = state.current_state.value
                state_changed_at_value = state.state_changed_at.isoformat()

            result.append(
                {
                    "student_id": student.id,
                    "student_code": student.student_code,
                    "full_name": student.full_name,
                    "current_state": current_state_value,
                    "state_changed_at": state_changed_at_value,
                }
            )
        return jsonify(result)
    finally:
        session.close()


@bp.route("/api/alerts")
@api_login_required
def get_alerts():
    """คืนรายชื่อนักศึกษาที่สถานะเป็น Missing อยู่ตอนนี้ (ใช้ทำช่องแจ้งเตือนสีแดงบน Dashboard)"""
    session = get_session()
    try:
        missing_states = (
            session.query(StudentState).filter_by(current_state=StateEnum.MISSING).all()
        )
        result = [
            {
                "student_id": state.student_id,
                "full_name": state.student.full_name,
                "missing_since": state.state_changed_at.isoformat(),
            }
            for state in missing_states
        ]
        return jsonify(result)
    finally:
        session.close()


# ==========================================================================
# จัดการคาบเรียน (Class Session) + Export รายงานท้ายคาบ
# ==========================================================================
@bp.route("/api/session/status")
@api_login_required
def get_session_status():
    """เช็คว่าตอนนี้มีคาบเรียนที่กำลังดำเนินอยู่หรือไม่ (ใช้ตอนโหลดหน้า Dashboard)"""
    report_service = current_app.config["REPORT_SERVICE"]
    return jsonify(report_service.get_session_status())


@bp.route("/api/session/start", methods=["POST"])
@csrf_protect
@api_login_required
def start_session():
    """อาจารย์กดปุ่ม 'เริ่มคลาส' - หาวิชาที่ตรงตารางเวลาขณะนี้อัตโนมัติ แล้วบันทึกเวลาเริ่ม"""
    report_service = current_app.config["REPORT_SERVICE"]
    return jsonify(report_service.start_session())


@bp.route("/api/session/end", methods=["POST"])
@csrf_protect
@api_login_required
def end_session():
    """อาจารย์กดปุ่ม 'จบคลาส' - บันทึกเวลาจบ พร้อมให้ดาวน์โหลดรายงานได้ทันที"""
    report_service = current_app.config["REPORT_SERVICE"]
    return jsonify(report_service.end_session())


@bp.route("/api/report/export")
@api_login_required
def export_report():
    """ดาวน์โหลดรายงานสรุปท้ายคาบเป็นไฟล์ CSV (เปิดด้วย Excel ได้ทันที)"""
    report_service = current_app.config["REPORT_SERVICE"]
    try:
        csv_bytes, filename = report_service.generate_report_csv()
    except ValueError as error:
        return jsonify({"success": False, "message": str(error)}), 400

    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )