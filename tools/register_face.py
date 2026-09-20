# -*- coding: utf-8 -*-
"""
tools/register_face.py
-------------------------
สคริปต์ช่วยเหลือสำหรับ "ลงทะเบียนใบหน้า" จากไฟล์รูปที่มีอยู่แล้ว
(เช่น รูปติดบัตรนักศึกษา หรือรูปที่พี่มีอยู่แล้วในเครื่อง) โดยไม่ต้องเปิดกล้อง

**สำคัญมาก - อ่านก่อนใช้งาน:**
ระบบจดจำใบหน้าโดยอ่าน path จากคอลัมน์ Student.face_image_path ใน "ฐานข้อมูล"
เท่านั้น ไม่ได้ตีความอะไรจาก "ชื่อไฟล์" เลย ถ้าพี่ไปเปลี่ยนชื่อไฟล์ในโฟลเดอร์
dataset/known_faces/ ตรงๆ ด้วยตัวเอง (ไม่ผ่านสคริปต์นี้หรือ capture_face.py)
path เดิมที่บันทึกไว้ใน DB จะหาไฟล์ไม่เจอ ทำให้ระบบจำหน้าใครไม่ได้เลย

วิธีใช้งาน:
    python tools/register_face.py --code 6704101306 --name "Kongkiat_J" --course 10301385 --image "C:\\path\\to\\photo.jpg"

ระบบจะทำให้อัตโนมัติ:
    1. คัดลอกไฟล์รูปเข้าไปเก็บใน dataset/known_faces/ ให้ (ถ้ายังไม่ได้อยู่ที่นั่น)
    2. สร้าง (หรืออัปเดต) ข้อมูลนักศึกษาในฐานข้อมูล ให้ face_image_path ชี้ไปที่ไฟล์
       ที่ถูกต้องเสมอ
    3. ลงทะเบียนวิชาตามรหัสวิชา (--course) ที่ระบุให้อัตโนมัติ

⚠️ รหัสนักศึกษา (--code) ต้อง "ไม่ซ้ำ" กับคนอื่นในระบบเด็ดขาด ถ้าซ้ำ ระบบจะเตือน
ก่อน overwrite ให้ (เช็คข้อมูลปัจจุบันก่อนได้ด้วย: python tools/check_students.py)
"""

import os
import sys
import shutil
import argparse

import face_recognition

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_session  # noqa: E402
from app.models import Student, Enrollment, Course  # noqa: E402

KNOWN_FACES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dataset",
    "known_faces",
)


def register(student_code: str, full_name: str, course_code: str, image_path: str) -> str:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"ไม่พบไฟล์รูปที่ path: {image_path}")

    try:
        image = face_recognition.load_image_file(image_path)
        face_count = len(face_recognition.face_locations(image))
    except Exception as exc:
        raise ValueError("ไม่สามารถอ่านหรือประมวลผลไฟล์รูปใบหน้าได้") from exc

    if face_count == 0:
        raise ValueError("รูปต้นแบบต้องมีใบหน้า 1 ใบ แต่ตรวจไม่พบใบหน้า")
    if face_count > 1:
        raise ValueError(f"รูปต้นแบบต้องมีใบหน้าเพียง 1 ใบ แต่ตรวจพบ {face_count} ใบ")

    os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
    target_path = os.path.abspath(image_path)

    # ถ้าไฟล์ต้นฉบับยังไม่ได้อยู่ในโฟลเดอร์ dataset/known_faces/ ให้คัดลอกเข้าไปก่อน
    # และตั้งชื่อไฟล์ใหม่ให้เป็นมาตรฐานเดียวกัน (รหัส_ชื่อ.นามสกุลไฟล์)
    if os.path.dirname(target_path) != os.path.abspath(KNOWN_FACES_DIR):
        safe_name = full_name.replace(" ", "_")
        ext = os.path.splitext(image_path)[1] or ".jpg"
        new_filename = f"{student_code}_{safe_name}{ext}"
        target_path = os.path.join(KNOWN_FACES_DIR, new_filename)
        shutil.copy2(image_path, target_path)
        print(f"[REGISTER] คัดลอกไฟล์ไปที่: {target_path}")
    else:
        print(f"[REGISTER] ไฟล์อยู่ในโฟลเดอร์ dataset/known_faces/ อยู่แล้ว ใช้ path เดิม: {target_path}")

    session = get_session()
    try:
        course = session.query(Course).filter_by(course_code=course_code).first()
        if course is None:
            raise ValueError(
                f"ไม่พบวิชารหัส '{course_code}' ในระบบ ตรวจสอบรหัสวิชาให้ถูกต้องก่อน"
            )

        existing = session.query(Student).filter_by(student_code=student_code).first()

        if existing is not None and existing.full_name != full_name:
            print(
                f"[REGISTER][คำเตือน] รหัส {student_code} มีอยู่แล้วในชื่อ '{existing.full_name}' "
                f"กำลังจะถูกเปลี่ยนเป็น '{full_name}' — ถ้าไม่ตั้งใจ ให้กด Ctrl+C ยกเลิกทันที!"
            )

        if existing is None:
            student = Student(
                student_code=student_code,
                full_name=full_name,
                face_image_path=target_path,
            )
            session.add(student)
            session.flush()  # flush เพื่อให้ student.id ถูกสร้างขึ้นก่อนใช้ผูก Enrollment
            print(f"[REGISTER] สร้างนักศึกษาใหม่ในระบบ: {student_code} - {full_name}")
        else:
            existing.full_name = full_name
            existing.face_image_path = target_path
            student = existing
            print(f"[REGISTER] อัปเดตข้อมูลนักศึกษา: {student_code} - {full_name}")

        # ลงทะเบียนวิชาตาม course_code ที่ระบุ (ถ้ายังไม่ได้ลงทะเบียนไว้)
        already_enrolled = (
            session.query(Enrollment)
            .filter_by(student_id=student.id, course_id=course.id)
            .first()
            is not None
        )
        if not already_enrolled:
            session.add(Enrollment(student_id=student.id, course_id=course.id))
            print(f"[REGISTER] ลงทะเบียนวิชา {course.course_code} ({course.course_name}) ให้แล้ว")
        else:
            print(f"[REGISTER] ลงทะเบียนวิชา {course.course_code} ไว้อยู่แล้ว")

        session.commit()
    finally:
        session.close()

    return target_path


def main():
    parser = argparse.ArgumentParser(
        description="ลงทะเบียนใบหน้าจากไฟล์รูปที่มีอยู่แล้ว (ไม่ต้องเปิดกล้อง)"
    )
    parser.add_argument("--code", required=True, help="รหัสนักศึกษา (ต้องไม่ซ้ำกับคนอื่น)")
    parser.add_argument("--name", required=True, help="ชื่อ-นามสกุล เช่น 'Kongkiat_J'")
    parser.add_argument("--course", required=True, help="รหัสวิชาที่จะลงทะเบียน เช่น 10301385")
    parser.add_argument("--image", required=True, help="path ของไฟล์รูปที่มีอยู่แล้วในเครื่อง")
    args = parser.parse_args()

    register(args.code, args.name, args.course, args.image)
    print("[REGISTER] เสร็จสิ้น! ตรวจสอบผลลัพธ์ได้ด้วย: python tools/check_students.py")


if __name__ == "__main__":
    main()