# -*- coding: utf-8 -*-
"""
app/face_recognition_service.py
---------------------------------
ไฟล์นี้คือหัวใจของ Phase 2: Facial Recognition Module
แบ่งเป็น 2 คลาส ตามหลัก Single Responsibility Principle (SRP):

1. FaceEncodingRepository
   - หน้าที่: โหลดรูปใบหน้าต้นแบบของนักศึกษาทุกคนจาก DB (คอลัมน์ face_image_path)
     แล้วเข้ารหัสเป็นตัวเลข (128-dimension vector) เก็บไว้ในหน่วยความจำ
   - เปรียบเสมือน "คลังข้อมูลใบหน้า" ที่พร้อมให้ค้นหา ไม่ยุ่งเกี่ยวกับกล้องหรือ Logic เปรียบเทียบ

2. FaceRecognizer
   - หน้าที่: รับภาพจากกล้อง (frame) มาค้นหาใบหน้า แล้วเทียบกับข้อมูลใน Repository
     ว่าตรงกับนักศึกษาคนไหน (หรือไม่ตรงกับใครเลย = คนแปลกหน้า)
   - ไม่รู้จักเรื่อง Database หรือกล้องเลย รับแค่ "ภาพ" เข้ามาประมวลผลเท่านั้น

การแยกแบบนี้ทำให้ทดสอบง่าย (Unit Test ได้อิสระ) และสอดคล้องกับ
Dependency Inversion: FaceRecognizer พึ่งพา "ข้อมูล encoding" ผ่าน Repository
ไม่ได้ผูกติดกับวิธีโหลดข้อมูลแบบเฉพาะเจาะจง
"""

import os
import numpy as np
import face_recognition

from app.database import get_session
from app.models import Student


class FaceEncodingRepository:
    """
    คลังเก็บ Face Encoding ของนักศึกษาทุกคนในระบบ
    โหลดข้อมูลจาก DB + ไฟล์รูปในโฟลเดอร์ dataset/known_faces/
    """

    def __init__(self, session_factory=get_session):
        # รับ session_factory เข้ามาแบบ Dependency Injection
        # เพื่อให้เปลี่ยน DB หรือ mock ตอนเทสได้ง่าย ไม่ hardcode
        self._session_factory = session_factory
        self._known_encodings: list[np.ndarray] = []
        self._known_student_ids: list[int] = []

    def load_known_faces(self):
        """
        อ่านรายชื่อนักศึกษาทั้งหมดจาก DB -> เปิดไฟล์รูปตาม face_image_path
        -> เข้ารหัสใบหน้า (encode) -> เก็บไว้ใน memory

        หมายเหตุ: ควรเรียกฟังก์ชันนี้ "ครั้งเดียวตอนเริ่มโปรแกรม" ไม่ใช่เรียกทุกเฟรม
        เพราะการเข้ารหัสใบหน้าเป็นงานที่ค่อนข้างหนัก (ใช้เวลาหลักวินาที/รูป)
        """
        session = self._session_factory()
        try:
            students = session.query(Student).all()

            self._known_encodings.clear()
            self._known_student_ids.clear()

            for student in students:
                encoding = self._encode_student_face(student)
                if encoding is not None:
                    self._known_encodings.append(encoding)
                    self._known_student_ids.append(student.id)

            print(
                f"[FACE-REPO] โหลดใบหน้าต้นแบบสำเร็จ "
                f"{len(self._known_encodings)}/{len(students)} คน"
            )
        finally:
            session.close()

    def _encode_student_face(self, student: Student):
        """
        เข้ารหัสใบหน้าของนักศึกษา 1 คน จากไฟล์รูปต้นแบบ
        คืนค่า None พร้อม warning ถ้าไม่พบไฟล์ หรือหารูปหน้าในภาพไม่เจอ
        """
        if not student.face_image_path:
            print(f"[FACE-REPO][WARN] {student.full_name} ไม่มี face_image_path ในระบบ")
            return None

        if not os.path.exists(student.face_image_path):
            print(
                f"[FACE-REPO][WARN] ไม่พบไฟล์รูปของ {student.full_name} "
                f"ที่ path: {student.face_image_path} "
                "(ลองใช้ tools/capture_face.py เพื่อถ่ายรูปใหม่)"
            )
            return None

        image = face_recognition.load_image_file(student.face_image_path)
        face_encodings = face_recognition.face_encodings(image)

        if len(face_encodings) == 0:
            print(
                f"[FACE-REPO][WARN] เจอไฟล์รูปของ {student.full_name} แล้ว "
                "แต่ตรวจไม่พบใบหน้าในภาพ (รูปอาจเบลอ/มืด/ไม่มีคนอยู่ในภาพ)"
            )
            return None

        if len(face_encodings) > 1:
            print(
                f"[FACE-REPO][WARN] รูปของ {student.full_name} มีหลายใบหน้า "
                "จึงปฏิเสธรูปต้นแบบที่ไม่ชัดเจน"
            )
            return None

        return face_encodings[0]

    @property
    def encodings(self) -> list:
        return self._known_encodings

    @property
    def student_ids(self) -> list:
        return self._known_student_ids

    def is_ready(self) -> bool:
        """เช็คว่ามีข้อมูลใบหน้าต้นแบบให้เทียบหรือยัง (กันเทียบกับคลังเปล่า)"""
        return len(self._known_encodings) > 0


class FaceRecognizer:
    """
    รับผิดชอบการ "ตรวจจับ + ระบุตัวตน" ใบหน้าในภาพสดจากกล้อง
    โดยเทียบกับข้อมูลที่ได้จาก FaceEncodingRepository
    """

    def __init__(self, repository: FaceEncodingRepository, tolerance: float = 0.5):
        """
        :param repository: คลังใบหน้าต้นแบบที่โหลดไว้แล้ว
        :param tolerance: ค่าความเข้มงวดในการเทียบใบหน้า
                           ยิ่งน้อย = เข้มงวดมาก (โอกาสจำผิดคนต่ำ แต่จำไม่ออกบ่อยขึ้น)
                           ค่ามาตรฐานทั่วไปคือ 0.6, แนะนำ 0.45-0.5 สำหรับงานเช็คชื่อ
                           ที่ต้องการความแม่นยำสูง (ป้องกันคนอื่นแอบเช็คชื่อแทนกัน)
        """
        self._repository = repository
        self._tolerance = tolerance

    def identify_faces_in_frame(self, frame: np.ndarray) -> list[dict]:
        """
        ตรวจจับใบหน้าทั้งหมดใน 1 เฟรม แล้วระบุตัวตนแต่ละใบหน้า

        :param frame: ภาพจากกล้อง (BGR, numpy array ตามมาตรฐาน OpenCV)
        :return: list ของ dict เช่น
                 [{"location": (top, right, bottom, left),
                   "student_id": 1 หรือ None ถ้าไม่รู้จัก}]
        """
        # face_recognition ต้องใช้ภาพแบบ RGB แต่ OpenCV อ่านภาพมาเป็น BGR
        # จึงต้อง "สลับช่องสี" ก่อนส่งเข้าไปประมวลผล
        #
        # หมายเหตุสำคัญ: frame[:, :, ::-1] ได้ผลลัพธ์ที่ถูกต้องแล้วในเชิงค่าสี
        # แต่ผลลัพธ์ที่ได้เป็น numpy view แบบ "non-contiguous" ในหน่วยความจำ
        # (แค่เปลี่ยนลำดับการอ่าน ไม่ได้ copy ข้อมูลจริง) ซึ่ง dlib (ที่ face_recognition
        # เรียกใช้งานอยู่ข้างใน) ต้องการ array แบบ contiguous เท่านั้น ไม่งั้นจะได้ error:
        #   TypeError: compute_face_descriptor(): incompatible function arguments
        # จึงต้องใช้ np.ascontiguousarray() บังคับให้ copy เป็น array ต่อเนื่องก่อนใช้งาน
        rgb_frame = np.ascontiguousarray(frame[:, :, ::-1])

        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        results = []
        for location, encoding in zip(face_locations, face_encodings):
            student_id = self._match_encoding(encoding)
            results.append({"location": location, "student_id": student_id})

        return results

    def _match_encoding(self, live_encoding: np.ndarray):
        """
        เทียบ encoding ของใบหน้าสด กับใบหน้าต้นแบบทุกคนในคลัง
        คืนค่า student_id ของคนที่ "ใกล้เคียงที่สุด" ถ้าใกล้เคียงพอ (ผ่าน tolerance)
        คืนค่า None ถ้าไม่มีใครตรงเลย (เช่น คนแปลกหน้า/ไม่ใช่นักศึกษาในระบบ)
        """
        if not self._repository.is_ready():
            return None

        # face_distance คำนวณ "ค่าความต่าง" ระหว่างใบหน้าสด กับทุกคนในคลัง
        # ยิ่งค่าน้อย = หน้าคล้ายกันมาก (0 คือเหมือนกันเป๊ะ)
        distances = face_recognition.face_distance(
            self._repository.encodings, live_encoding
        )

        best_match_index = int(np.argmin(distances))
        best_distance = distances[best_match_index]

        if best_distance <= self._tolerance:
            return self._repository.student_ids[best_match_index]

        return None
