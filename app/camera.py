# -*- coding: utf-8 -*-
"""
app/camera.py
--------------
คลาสนี้รับผิดชอบ "การจัดการกล้อง Webcam" เพียงอย่างเดียว (SRP)
ไม่รู้จักเรื่อง Face Recognition หรือ Business Logic ใด ๆ ทั้งสิ้น
เป้าหมายคือให้เปิด/ปิดกล้องได้อย่างปลอดภัย ไม่ลืมปล่อยทรัพยากร (release)

ทำไมต้องแยกออกมาเป็นคลาสต่างหาก (ไม่รวมกับ FaceRecognizer)?
เพราะถ้าวันหนึ่งพี่เปลี่ยนจาก Webcam ธรรมดา ไปใช้กล้อง IP Camera
หรือ USB Camera หลายตัว เราจะแก้แค่ไฟล์นี้ไฟล์เดียว (Open/Closed Principle)
ตัว FaceRecognizer จะไม่กระทบเลย เพราะมันรับแค่ "ภาพ (frame)" เข้าไปประมวลผล
"""

import cv2


class CameraStream:
    """
    ครอบ cv2.VideoCapture ให้ใช้งานง่ายและปลอดภัยขึ้น
    รองรับการใช้งานแบบ Context Manager (with-statement) เพื่อการันตีว่า
    กล้องจะถูกปล่อย (release) เสมอ ไม่ว่าจะเกิด error หรือไม่ก็ตาม

    ตัวอย่างการใช้งาน:
        with CameraStream(source=0) as cam:
            frame = cam.read_frame()
            ...
    """

    def __init__(self, source: int = 0):
        """
        :param source: index ของกล้อง (0 = กล้องหลักของเครื่อง)
                        ถ้ามีกล้องหลายตัว ลองเปลี่ยนเป็น 1, 2, ...
        """
        self._source = source
        self._capture: cv2.VideoCapture | None = None

    def start(self) -> "CameraStream":
        """เปิดกล้อง คืนค่า self เพื่อให้เขียนแบบ chain ได้ เช่น CameraStream(0).start()"""
        self._capture = cv2.VideoCapture(self._source)
        if not self._capture.isOpened():
            raise RuntimeError(
                f"ไม่สามารถเปิดกล้อง source={self._source} ได้ "
                "ตรวจสอบว่ากล้องต่ออยู่ และไม่มีโปรแกรมอื่นใช้กล้องนี้อยู่"
            )
        return self

    def read_frame(self):
        """
        อ่านภาพ 1 เฟรมจากกล้อง
        คืนค่า numpy array (BGR ตามมาตรฐาน OpenCV) หรือ None ถ้าอ่านไม่สำเร็จ
        """
        if self._capture is None:
            raise RuntimeError("ต้องเรียก start() ก่อนเรียก read_frame() เสมอ")

        success, frame = self._capture.read()
        if not success:
            return None
        return frame

    def release(self):
        """ปล่อยทรัพยากรกล้อง สำคัญมาก ไม่ทำจะทำให้กล้องค้าง เปิดซ้ำไม่ได้"""
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    # ---------------- รองรับ with-statement ----------------
    def __enter__(self) -> "CameraStream":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()