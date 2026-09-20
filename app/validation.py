import re


USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")


def validate_login_input(username: str, password: str) -> str | None:
    """Return a user-facing validation message, or None when input is valid."""
    if not username:
        return "กรุณากรอกชื่อผู้ใช้"
    if len(username) > 50 or not USERNAME_RE.fullmatch(username):
        return "ชื่อผู้ใช้ไม่ถูกต้อง"

    if not password:
        return "กรุณากรอกรหัสผ่าน"
    if len(password) > 128:
        return "รหัสผ่านยาวเกินไป"

    return None
