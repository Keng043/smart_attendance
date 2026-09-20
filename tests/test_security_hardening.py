from app import create_app
from app.database import get_session
from app.models import Instructor
from werkzeug.security import generate_password_hash


def make_client(role="INSTRUCTOR"):
    app, video = create_app()
    app.config.update(TESTING=True, SECRET_KEY="test-security")
    db = get_session()
    try:
        user = db.query(Instructor).filter_by(username="pytest_security_user").first()
        if user:
            db.delete(user)
            db.commit()
        user = Instructor(
            username="pytest_security_user",
            password_hash=generate_password_hash("correct-password"),
            full_name="Security Test",
            role=role,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()
    return app.test_client(), video


def login(client):
    client.get("/login")
    with client.session_transaction() as s:
        token = s["_csrf_token"]
    return client.post(
        "/login",
        data={"username": "pytest_security_user", "password": "correct-password", "csrf_token": token},
    )


def cleanup(video):
    db = get_session()
    try:
        user = db.query(Instructor).filter_by(username="pytest_security_user").first()
        if user:
            db.delete(user)
            db.commit()
    finally:
        db.close()
        video.release()


def test_security_headers_are_present():
    client, video = make_client()
    try:
        response = client.get("/login")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    finally:
        cleanup(video)


def test_admin_endpoint_rejects_instructor_and_ignores_session_role_tampering():
    client, video = make_client("INSTRUCTOR")
    try:
        login(client)
        response = client.get("/api/admin/audit")
        assert response.status_code == 403

        with client.session_transaction() as s:
            s["instructor_role"] = "ADMIN"

        response = client.get("/api/admin/audit")
        assert response.status_code == 403
    finally:
        cleanup(video)
