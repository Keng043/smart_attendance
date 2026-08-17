# -*- coding: utf-8 -*-
"""
app/models.py
--------------
ไฟล์นี้กำหนด "โครงสร้างข้อมูล" ทั้งหมดของระบบ ด้วย SQLAlchemy ORM
การใช้ ORM (แทนการเขียน Raw SQL) ช่วยป้องกัน SQL Injection โดยธรรมชาติ
เพราะ SQLAlchemy จะทำการ escape ค่าต่าง ๆ ให้เราโดยอัตโนมัติ

ตารางที่ออกแบบไว้ (ตาม OOP + SOLID):
1. Student        -> ข้อมูลนักศึกษา + รูปใบหน้าต้นแบบ
2. Course         -> ข้อมูลรายวิชา (เพิ่มเติมจาก requirement เดิม
                      เพื่อรองรับ Business Logic "เช็คว่ามีสิทธิ์เรียนคลาสนี้ไหม")
3. Enrollment     -> ตารางกลาง (Many-to-Many) เชื่อม Student <-> Course
4. AttendanceLog  -> บันทึกประวัติการเช็คชื่อเข้าเรียน
5. StudentState   -> สถานะปัจจุบันของนักศึกษา (In_Class / Away / Missing)
                      พร้อม Timestamp เพื่อคำนวณเวลาสำหรับ Timer

หมายเหตุ (SOLID - Single Responsibility):
คลาสเหล่านี้มีหน้าที่แค่ "เก็บโครงสร้างข้อมูล" (Data Structure)
ส่วน Logic การคำนวณเวลา/ตรวจสอบ Alert จะถูกแยกไปเขียนใน Service/Controller
ใน Phase 3 เพื่อไม่ให้ Model รับผิดชอบหลายอย่างเกินไป (ผิดหลัก SRP)
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Time,
    ForeignKey,
    Enum as SqlEnum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


# ======================================================================
# ENUM: สถานะของนักศึกษา ณ ขณะนั้น
# ใช้ Enum แทน String ธรรมดา เพื่อป้องกันการพิมพ์ผิด (Type Safety)
# ======================================================================
class StateEnum(str, enum.Enum):
    NOT_ARRIVED = "Not_Arrived"  # ยังไม่มาเรียน (ค่าเริ่มต้นก่อนเดินผ่านกล้องครั้งแรก)
    IN_CLASS = "In_Class"        # อยู่ในห้องเรียน (สแกนหน้าผ่านกล้องหน้าประตูแล้ว)
    AWAY = "Away"                # เดินออกจากห้อง (สแกนหน้าผ่านกล้องอีกครั้ง) กำลังจับเวลา
    MISSING = "Missing"          # ออกไปนานเกินกำหนด (เกิน Threshold) ต้องแจ้งเตือนอาจารย์


# ======================================================================
# TABLE 1: Student (นักศึกษา)
# ======================================================================
class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # รหัสนักศึกษา เช่น "10301234" -> ต้องไม่ซ้ำกัน (unique)
    student_code = Column(String(20), unique=True, nullable=False, index=True)

    full_name = Column(String(100), nullable=False)

    # Path ของไฟล์รูปใบหน้าต้นแบบ (ใช้ตอน Encode ใน Phase 2)
    # เช่น "dataset/known_faces/10301234_Kongkiat.jpg"
    face_image_path = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # ---------------- Relationships ----------------
    # นักศึกษา 1 คน ลงทะเบียนได้หลายวิชา (ผ่านตาราง Enrollment)
    enrollments = relationship(
        "Enrollment", back_populates="student", cascade="all, delete-orphan"
    )
    # นักศึกษา 1 คน มีประวัติการเช็คชื่อได้หลายครั้ง
    attendance_logs = relationship(
        "AttendanceLog", back_populates="student", cascade="all, delete-orphan"
    )
    # นักศึกษา 1 คน มีสถานะปัจจุบันแบบ one-to-one
    # (เก็บเป็นแถวเดียวที่อัปเดตทับไปเรื่อย ๆ เพื่อให้ query สถานะล่าสุดได้เร็ว)
    state = relationship(
        "StudentState",
        back_populates="student",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Student {self.student_code} - {self.full_name}>"


# ======================================================================
# TABLE 2: Course (รายวิชา)
# ======================================================================
class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_code = Column(String(20), unique=True, nullable=False)  # เช่น "CS101"
    course_name = Column(String(150), nullable=False)              # เช่น "Intro to Programming"

    enrollments = relationship(
        "Enrollment", back_populates="course", cascade="all, delete-orphan"
    )
    attendance_logs = relationship("AttendanceLog", back_populates="course")

    def __repr__(self):
        return f"<Course {self.course_code} - {self.course_name}>"


# ======================================================================
# TABLE 3: Enrollment (ตารางกลางเชื่อม Student <-> Course)
# ใช้เช็คว่า "นักศึกษาคนนี้มีสิทธิ์เรียนวิชานี้หรือไม่"
# ======================================================================
class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_student_course"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)

    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")

    def __repr__(self):
        return f"<Enrollment student_id={self.student_id} course_id={self.course_id}>"


# ======================================================================
# TABLE 4: AttendanceLog (บันทึกประวัติการเช็คชื่อ)
# ======================================================================
class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)

    check_in_time = Column(DateTime, default=datetime.utcnow)

    # สถานะการเช็คชื่อ เช่น "Present" (มาเรียน), "Late" (มาสาย)
    status = Column(String(20), default="Present")

    student = relationship("Student", back_populates="attendance_logs")
    course = relationship("Course", back_populates="attendance_logs")

    def __repr__(self):
        return f"<AttendanceLog student_id={self.student_id} time={self.check_in_time}>"


# ======================================================================
# TABLE 5: StudentState (สถานะปัจจุบัน + Timestamp สำหรับจับเวลา)
# นี่คือ "ใจกลาง" ของ Business Logic เรื่อง Timer/Alert ใน Phase 3
# ======================================================================
class StudentState(Base):
    __tablename__ = "student_states"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # one-to-one กับ Student (unique เพื่อบังคับว่า 1 คนมีสถานะเดียว)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True, nullable=False)

    current_state = Column(
        SqlEnum(StateEnum), nullable=False, default=StateEnum.NOT_ARRIVED
    )

    # เวลาที่ "เปลี่ยนสถานะล่าสุด" -> ใช้คำนวณว่าผ่านไปกี่นาทีแล้ว
    # เช่น ถ้า current_state = Away และ state_changed_at คือ 10:00
    # ผ่านไป 15 นาที (10:15) แล้วยังไม่กลับมาสแกน -> Controller จะเปลี่ยนเป็น Missing
    state_changed_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="state")

    def __repr__(self):
        return f"<StudentState student_id={self.student_id} state={self.current_state}>"


# ======================================================================
# TABLE 6: AlertLog (ประวัติการแจ้งเตือน Missing) — เพิ่มใน Phase 5
# ------------------------------------------------------------------------
# StudentState เก็บได้แค่ "สถานะปัจจุบัน" อย่างเดียว ถ้านักศึกษาเคยหายไป
# เกินเวลาแล้วกลับมาทัน สถานะจะถูกเปลี่ยนกลับเป็น In_Class ทับไปเลย
# ทำให้ตอนสร้างรายงานท้ายคาบ ไม่มีทางรู้ว่า "เคยหายไปตอนไหนบ้าง"
# ตารางนี้จึงทำหน้าที่เป็น "ประวัติ" (Log) แยกไว้ ไม่ทับกับสถานะปัจจุบัน
# ทุกครั้งที่ AttendanceController ตีสถานะ Missing จะบันทึกแถวใหม่ที่นี่เสมอ
# ======================================================================
class AlertLog(Base):
    __tablename__ = "alert_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)

    # เวลาที่ระบบตีสถานะ Missing (คือเวลาที่ตรวจพบว่าเกินกำหนดแล้ว)
    triggered_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student")

    def __repr__(self):
        return f"<AlertLog student_id={self.student_id} at={self.triggered_at}>"


# ======================================================================
# TABLE 7: ClassSession (บันทึกเวลาเริ่ม/จบคาบเรียน) — เพิ่มใน Phase 5
# ------------------------------------------------------------------------
# ใช้เป็น "จุดอ้างอิงเวลา" สำหรับคำนวณว่านักศึกษาคนไหน "มาสาย" (เทียบกับ
# started_at) และใช้เป็นขอบเขตเวลาตอนสร้างรายงานท้ายคาบ (ระหว่าง started_at
# ถึง ended_at) แทนการต้องตั้ง "เวลาเข้าเรียน" fix ตายตัวในโค้ด เพราะเวลาเริ่ม
# คาบจริงอาจไม่ตรงกันทุกวัน อาจารย์กดปุ่ม "เริ่มคลาส" เองตอนจะเริ่มสอนจริง
# ======================================================================
class ClassSession(Base):
    __tablename__ = "class_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)

    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)  # None = คาบยังไม่จบ (กำลังดำเนินอยู่)

    course = relationship("Course")

    def __repr__(self):
        return f"<ClassSession course_id={self.course_id} started={self.started_at} ended={self.ended_at}>"


# ======================================================================
# TABLE 8: CourseSchedule (ตารางเวลาเรียนของแต่ละวิชา)
# ------------------------------------------------------------------------
# 1 วิชาอาจเรียนได้หลายวันต่อสัปดาห์ (เช่น จันทร์ + พุธ) จึงแยกเป็นตารางย่อย
# แทนการเก็บฟิลด์ day/time ไว้ในตาราง Course ตรงๆ (1 Course -> หลาย Schedule)
#
# day_of_week ใช้รูปแบบเดียวกับ Python's datetime.weekday(): 0=จันทร์ ... 6=อาทิตย์
# เพื่อให้เทียบกับเวลาปัจจุบันได้ตรงๆ โดยไม่ต้องแปลงกลับไปกลับมา
#
# ใช้เป็นตัวตัดสินว่า "ขณะนี้เป็นคาบเรียนของวิชาไหน" (ดู app/schedule_service.py)
# แทนการ fix วิชาเดียวตายตัวแบบเดิม (DEFAULT_COURSE_ID) เพราะระบบตอนนี้ต้อง
# รองรับหลายวิชาพร้อมกัน แล้วแยกแยะอัตโนมัติจากเวลาปัจจุบัน
# ======================================================================
class CourseSchedule(Base):
    __tablename__ = "course_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)

    day_of_week = Column(Integer, nullable=False)  # 0=จันทร์, 1=อังคาร, ..., 6=อาทิตย์
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    course = relationship("Course")

    def __repr__(self):
        return (
            f"<CourseSchedule course_id={self.course_id} "
            f"day={self.day_of_week} {self.start_time}-{self.end_time}>"
        )


# ======================================================================
# TABLE 9: Instructor (บัญชีอาจารย์ - สำหรับ Login เข้าดู Dashboard/รายงาน)
# ------------------------------------------------------------------------
# เก็บ password แบบ hash เท่านั้น (ไม่เก็บ plain text) ใช้ werkzeug.security
# ที่ติดมากับ Flask อยู่แล้ว ไม่ต้องลง library เพิ่ม
# ======================================================================
class Instructor(Base):
    __tablename__ = "instructors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<Instructor {self.username}>"