# -*- coding: utf-8 -*-
"""
tools/capture_face.py
------------------------
สคริปต์ช่วยเหลือ (ไม่ใช่ส่วนหลักของระบบ) สำหรับ "ลงทะเบียนใบหน้า" นักศึกษาใหม่
โดยถ่ายรูปสด ๆ จากเว็บแคม แทนการหารูปนักศึกษามาเอง

ประโยชน์ตอนพรีเซนต์: พี่สามารถใช้ "หน้าตัวเอง" แทน Kongkiat ได้เลย
โดยไม่ต้องไปหารูปใครมาทดสอบ

วิธีใช้งาน:
    python tools/capture_face.py --code 6704101306 --name "Kongkiat_J" --course 10301385

ขั้นตอน:
    1. กล้องจะเปิดขึ้น เห็นหน้าตัวเองในหน้าต่าง
    2. กด SPACE เพื่อถ่ายรูป (ควรอยู่ในที่แสงสว่างพอ หน้าไม่เอียงมาก)
    3. ระบบจะบันทึกไฟล์ลง dataset/known_faces/
       และอัปเดต (หรือสร้างใหม่) ข้อมูลนักศึกษาในฐานข้อมูลให้ face_image_path ชี้ไปที่ไฟล์นี้
    4. กด Q เพื่อออกโดยไม่บันทึก
"""

import os
import sys
import argparse

import cv2

# เพิ่ม root ของโปรเจกต์เข้า sys.path เพื่อให้ import app.* ได้
# แม้จะรันสคริปต์นี้จากโฟลเดอร์ tools/ ก็ตาม
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_session  # noqa: E402
from app.models import Student, Enrollment, Course  # noqa: E402
from app.config import CAMERA_SOURCE  # noqa: E402

KNOWN_FACES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dataset",
    "known_faces",
)


def capture_photo_from_webcam():
    """
    เปิดกล้อง แสดงภาพสด ๆ ให้ผู้ใช้เห็น
    กด SPACE = ถ่ายรูป (คืนค่าภาพนั้น), กด Q = ยกเลิก (คืนค่า None)
    """
    cap = cv2.VideoCapture(CAMERA_SOURCE)
    if not cap.isOpened():
        raise RuntimeError("ไม่สามารถเปิดกล้องได้ ตรวจสอบว่ากล้องต่ออยู่และไม่มีโปรแกรมอื่นใช้งาน")

    captured_frame = None
    print("[CAPTURE] กด SPACE เพื่อถ่ายรูป, กด Q เพื่อยกเลิก")

    try:
        while True:
            success, frame = cap.read()
            if not success:
                continue

            # วาดข้อความแนะนำลงบนภาพ เพื่อให้ผู้ใช้รู้ว่าต้องกดปุ่มไหน
            preview = frame.copy()
            cv2.putText(
                preview,
                "SPACE = Capture | Q = Cancel",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )
            cv2.imshow("Capture Face - Smart Attendance System", preview)

            key = cv2.waitKey(1) & 0xFF
            if key == ord(" "):  # SPACE
                captured_frame = frame
                break
            elif key == ord("q"):  # Q
                captured_frame = None
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return captured_frame


def save_student_face(student_code: str, full_name: str, course_code: str, frame) -> str:
    """
    บันทึกภาพที่ถ่ายได้ลงไฟล์ในโฟลเดอร์ dataset/known_faces/
    แล้ว insert หรือ update ข้อมูลนักศึกษาในฐานข้อมูลให้ชี้ไปยังไฟล์นี้
    พร้อมลงทะเบียนวิชาตาม course_code ที่ระบุ

    :return: path ของไฟล์รูปที่บันทึกสำเร็จ
    :raises ValueError: ถ้าไม่พบวิชาตาม course_code ที่ระบุ
    """
    os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

    # ตั้งชื่อไฟล์แบบไม่มีช่องว่าง เพื่อป้องกันปัญหา path บน OS ต่าง ๆ
    safe_name = full_name.replace(" ", "_")
    file_name = f"{student_code}_{safe_name}.jpg"
    file_path = os.path.join(KNOWN_FACES_DIR, file_name)

    cv2.imwrite(file_path, frame)
    print(f"[CAPTURE] บันทึกรูปสำเร็จ: {file_path}")

    session = get_session()
    try:
        course = session.query(Course).filter_by(course_code=course_code).first()
        if course is None:
            raise ValueError(
                f"ไม่พบวิชารหัส '{course_code}' ในระบบ "
                "ตรวจสอบรหัสวิชาให้ถูกต้อง (ดูรหัสวิชาที่มีอยู่ได้จาก tools/check_students.py "
                "หรือฐานข้อมูลตาราง courses)"
            )

        student = (
            session.query(Student).filter_by(student_code=student_code).first()
        )

        if student is None:
            # ถ้ายังไม่มีรหัสนี้ในระบบ -> สร้างนักศึกษาใหม่
            student = Student(
                student_code=student_code,
                full_name=full_name,
                face_image_path=file_path,
            )
            session.add(student)
            session.flush()  # flush เพื่อให้ student.id ถูกสร้างขึ้นก่อนใช้ผูก Enrollment
            print(f"[CAPTURE] สร้างนักศึกษาใหม่ในระบบ: {student_code} - {full_name}")
        else:
            # ถ้ามีอยู่แล้ว -> แค่อัปเดต path รูปใบหน้าต้นแบบ (เผื่อถ่ายใหม่)
            student.face_image_path = file_path
            student.full_name = full_name
            print(f"[CAPTURE] อัปเดตรูปใบหน้าของ: {student_code} - {full_name}")

        # ลงทะเบียนวิชาตาม course_code ที่ระบุ (ถ้ายังไม่ได้ลงทะเบียนไว้)
        # สำคัญมาก ถ้าไม่ทำตรงนี้ ระบบจะจำหน้าได้ แต่เช็คชื่อไม่ผ่าน เพราะเช็คสิทธิ์
        # Enrollment ไม่เจอ
        already_enrolled = (
            session.query(Enrollment)
            .filter_by(student_id=student.id, course_id=course.id)
            .first()
            is not None
        )
        if not already_enrolled:
            session.add(Enrollment(student_id=student.id, course_id=course.id))
            print(f"[CAPTURE] ลงทะเบียนวิชา {course.course_code} ({course.course_name}) ให้แล้ว")
        else:
            print(f"[CAPTURE] ลงทะเบียนวิชา {course.course_code} ไว้อยู่แล้ว")

        session.commit()
    finally:
        session.close()

    return file_path


def main():
    parser = argparse.ArgumentParser(
        description="ถ่ายรูปใบหน้าจากเว็บแคม เพื่อลงทะเบียนเป็นนักศึกษาในระบบ"
    )
    parser.add_argument("--code", required=True, help="รหัสนักศึกษา เช่น 6704101306")
    parser.add_argument("--name", required=True, help="ชื่อ-นามสกุล เช่น 'Kongkiat_J'")
    parser.add_argument("--course", required=True, help="รหัสวิชาที่จะลงทะเบียน เช่น 10301385")
    args = parser.parse_args()

    frame = capture_photo_from_webcam()
    if frame is None:
        print("[CAPTURE] ยกเลิกการถ่ายรูป ไม่มีการบันทึกข้อมูล")
        return

    save_student_face(args.code, args.name, args.course, frame)
    print("[CAPTURE] เสร็จสิ้น! ลองรัน demo_face_recognition.py เพื่อทดสอบระบบจดจำใบหน้าได้เลย")


if __name__ == "__main__":
    main()