import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.database import get_session
from app.models import Instructor, AuditLog


@pytest.fixture()
def client():
    app, video = create_app()
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    client = app.test_client()

    session = get_session()
    try:
        existing = session.query(Instructor).filter_by(username="pytest_auth_user").first()
        if existing:
            session.delete(existing)
            session.commit()
        instructor = Instructor(
            username="pytest_auth_user",
            password_hash=generate_password_hash("correct-password"),
            full_name="Pytest Instructor",
        )
        session.add(instructor)
        session.commit()
    finally:
        session.close()

    yield client

    session = get_session()
    try:
        instructor = session.query(Instructor).filter_by(username="pytest_auth_user").first()
        if instructor:
            session.delete(instructor)
            session.commit()
    finally:
        session.close()
        video.release()


def csrf_token(client):
    client.get("/login")
    with client.session_transaction() as flask_session:
        return flask_session["_csrf_token"]


def login_data(client, password="correct-password"):
    return {
        "username": "pytest_auth_user",
        "password": password,
        "csrf_token": csrf_token(client),
    }


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_api_requires_login(client):
    response = client.get("/api/status")
    assert response.status_code == 401
    assert response.get_json()["success"] is False


def test_login_requires_csrf(client):
    response = client.post(
        "/login",
        data={"username": "pytest_auth_user", "password": "correct-password"},
    )
    assert response.status_code == 400


def test_login_rejects_wrong_password(client):
    response = client.post("/login", data=login_data(client, "wrong-password"))
    assert response.status_code == 200
    assert "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง" in response.get_data(as_text=True)


def test_login_sets_session_and_records_audit(client):
    response = client.post(
        "/login",
        data=login_data(client),
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]

    with client.session_transaction() as flask_session:
        assert flask_session["instructor_name"] == "Pytest Instructor"
        instructor_id = flask_session["instructor_id"]

    session = get_session()
    try:
        event = (
            session.query(AuditLog)
            .filter_by(action="USER_LOGIN", instructor_id=instructor_id)
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert event is not None
    finally:
        session.close()


def test_external_next_redirect_is_blocked(client):
    response = client.post(
        "/login?next=https://example.com",
        data=login_data(client),
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_logout_requires_csrf_and_records_audit(client):
    client.post("/login", data=login_data(client))

    response = client.post("/logout", follow_redirects=False)
    assert response.status_code == 400

    token = csrf_token(client)
    response = client.post(
        "/logout",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    with client.session_transaction() as flask_session:
        assert "instructor_id" not in flask_session

    session = get_session()
    try:
        event = (
            session.query(AuditLog)
            .filter_by(action="USER_LOGOUT")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert event is not None
    finally:
        session.close()


def test_session_start_requires_csrf(client):
    client.post("/login", data=login_data(client))
    response = client.post("/api/session/start")
    assert response.status_code == 400


def test_session_end_requires_csrf(client):
    client.post("/login", data=login_data(client))
    response = client.post("/api/session/end")
    assert response.status_code == 400
