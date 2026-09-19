"""Audit logging for security-sensitive application events."""

from datetime import datetime

from app.models import AuditLog


def record_event(session, action: str, instructor_id: int | None = None, details: str | None = None):
    """Persist a small security audit event; never store passwords or face data."""
    session.add(
        AuditLog(
            instructor_id=instructor_id,
            action=action,
            details=details,
            created_at=datetime.utcnow(),
        )
    )
