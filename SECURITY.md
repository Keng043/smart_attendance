# Security Notes

## Scope
This document records the current defensive security baseline for Smart Attendance.

## Protected assets
- Instructor authentication data
- Student identity and attendance records
- Face image files used by the recognition pipeline
- Session cookies
- Audit history

## Current controls
- Passwords are stored as Werkzeug password hashes, not plaintext.
- Protected dashboard/API routes require an authenticated instructor session.
- Session cookies use HttpOnly and SameSite=Lax.
- Secure cookies can be enabled with `SESSION_COOKIE_SECURE=1` when HTTPS is used.
- Login and logout events are recorded in `audit_logs`.
- SQLAlchemy ORM is used for database access.
- Face datasets, SQLite databases, virtual environments, and Python caches are ignored by Git.
- Login `next` redirects are restricted to local application paths to reduce open-redirect risk.

## Operational rules
- Never commit `dataset/known_faces/`, `attendance.db`, passwords, `.env` files, or private keys.
- Use HTTPS before enabling `SESSION_COOKIE_SECURE=1`.
- Use a unique production `SECRET_KEY` supplied through the environment.
- Keep biometric data on the local machine unless there is an explicit approved reason to transfer it.

## Next security work
1. Add CSRF protection for state-changing browser requests.
2. Add role/permission checks if multiple instructor roles are introduced.
3. Add security-focused tests for authentication and authorization.
4. Review biometric spoofing/liveness risks.
5. Add retention/deletion procedures for face data and audit records.
