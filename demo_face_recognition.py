# -*- coding: utf-8 -*-
"""
demo_face_recognition.py
---------------------------
สคริปต์ทดสอบ Phase 2 แบบสแตนด์อโลน (ยังไม่เกี่ยวกับ Flask/Web)
เปิดกล้อง Webcam ขึ้นมาตรง ๆ แล้ววาดกรอบ + ชื่อนักศึกษาที่จำได้ทับบนภาพสด

จุดประสงค์: ให้พี่เทสได้ว่า FaceEncodingRepository + FaceRecognizer + CameraStream
ที่เขียนใน Phase 2 ทำงานถูกต้องหรือไม่ ก่อนจะเอาไปต่อกับ Web Server ใน Phase 4
(แยกเทสเป็นส่วน ๆ ตาม Phase ช่วยให้ debug ง่ายกว่ารวมทุกอย่างแล้วค่อยเทส)

วิธีรัน:
    python demo_face_recognition.py

กด Q บนหน้าต่างวิดีโอ เพื่อออกจากโปรแกรม
"""

import cv2

from app.camera import CameraStream
from app.face_recognition_service import FaceEncodingRepository, FaceRecognizer
from app.database import get_session
from app.models import Student
from app.config import CAMERA_SOURCE


def get_student_name_by_id(student_id: int) -> str:
    """ดึงชื่อนักศึกษาจาก DB ตาม id (ใช้แสดงผลบนภาพ)"""
    session = get_session()
    try:
        student = session.query(Student).filter_by(id=student_id).first()
        return student.full_name if student else "Unknown"
    finally:
        session.close()


def draw_face_box(frame, location, label, color):
    """
    วาดกรอบสี่เหลี่ยมล้อมใบหน้า + ป้ายชื่อกำกับไว้ด้านบน
    :param location: tuple (top, right, bottom, left) ตามที่ face_recognition คืนค่ามา
    """
    top, right, bottom, left = location
    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

    # วาดพื้นหลังสี่เหลี่ยมทึบไว้ใต้กรอบ เพื่อให้ตัวหนังสือชื่ออ่านง่าย ไม่จมกับพื้นหลัง
    cv2.rectangle(frame, (left, bottom), (right, bottom + 30), color, cv2.FILLED)
    cv2.putText(
        frame,
        label,
        (left + 6, bottom + 22),
        cv2.FONT_HERSHEY_DUPLEX,
        0.6,
        (255, 255, 255),
        1,
    )


def main():
    print("[DEMO] กำลังโหลดใบหน้าต้นแบบจากฐานข้อมูล ...")
    repository = FaceEncodingRepository()
    repository.load_known_faces()

    if not repository.is_ready():
        print(
            "[DEMO][WARN] ไม่พบใบหน้าต้นแบบเลยในระบบ! "
            "ใบหน้าทุกคนที่เจอจะถูกจัดเป็น 'Unknown' ทั้งหมด\n"
            "แนะนำให้รัน: python tools/capture_face.py --code 10301234 --name \"Kongkiat Somchai\""
        )

    recognizer = FaceRecognizer(repository, tolerance=0.5)

    print("[DEMO] เปิดกล้อง ... กด Q เพื่อออกจากโปรแกรม")
    with CameraStream(source=CAMERA_SOURCE) as cam:
        while True:
            frame = cam.read_frame()
            if frame is None:
                continue

            results = recognizer.identify_faces_in_frame(frame)

            for face in results:
                if face["student_id"] is not None:
                    name = get_student_name_by_id(face["student_id"])
                    color = (0, 200, 0)  # เขียว = จำได้ (Known)
                else:
                    name = "Unknown"
                    color = (0, 0, 255)  # แดง = จำไม่ได้ (Unknown)

                draw_face_box(frame, face["location"], name, color)

            cv2.imshow("Smart Attendance - Face Recognition Demo (Phase 2)", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()
    print("[DEMO] ปิดโปรแกรมเรียบร้อย")


if __name__ == "__main__":
    main()