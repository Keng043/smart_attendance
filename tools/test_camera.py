"""
tools/test_camera.py
-----------------------
สคริปต์สำหรับสแกนหา Index ของกล้องที่เชื่อมต่ออยู่กับ Windows
ใช้เพื่อหาว่า Iriun Webcam ซ่อนอยู่ที่หมายเลขอะไร
"""

import cv2

def scan_cameras():
    print("🔍 กำลังสแกนหาพอร์ตกล้อง (Index 0 ถึง 4)...")
    available_cameras = []
    
    for i in range(5):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) # ใช้ CAP_DSHOW เพื่อให้รันบน Windows ได้เร็วขึ้น
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                height, width, _ = frame.shape
                print(f"✅ พบกล้องที่ Index: [{i}] | ความละเอียดภาพ: {width}x{height}")
                available_cameras.append(i)
            cap.release()
        else:
            print(f"❌ ไม่พบกล้องที่ Index: [{i}]")
            
    print("-" * 40)
    if available_cameras:
        print(f"🎯 สรุป: กล้องที่ใช้งานได้คือ Index {available_cameras}")
        print("💡 ให้นำตัวเลขนี้ไปใส่ในตัวแปร CAMERA_SOURCE ในไฟล์หลัก")
    else:
        print("⚠️ ไม่พบกล้องเลย! ตรวจสอบการเชื่อมต่อ Iriun อีกครั้ง")

if __name__ == "__main__":
    scan_cameras()