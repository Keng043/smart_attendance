from app.validation import validate_login_input


def test_valid_login_input():
    assert validate_login_input("teacher_01", "correct-password") is None


def test_empty_username_is_rejected():
    assert validate_login_input("", "password") == "กรุณากรอกชื่อผู้ใช้"


def test_invalid_username_format_is_rejected():
    assert validate_login_input("admin@example.com", "password") == "ชื่อผู้ใช้ไม่ถูกต้อง"


def test_empty_password_is_rejected():
    assert validate_login_input("teacher", "") == "กรุณากรอกรหัสผ่าน"


def test_oversized_password_is_rejected():
    assert validate_login_input("teacher", "x" * 129) == "รหัสผ่านยาวเกินไป"
