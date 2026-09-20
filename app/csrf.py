import hmac
import secrets

from flask import abort, session, request


CSRF_SESSION_KEY = "_csrf_token"


def get_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf():
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return

    expected = session.get(CSRF_SESSION_KEY)
    supplied = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")

    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        abort(400, description="CSRF token invalid")


def csrf_protect(view_func):
    from functools import wraps

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        validate_csrf()
        return view_func(*args, **kwargs)

    return wrapped
