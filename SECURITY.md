# Security Notes

## Scope

Current defensive security baseline for Smart Attendance, including authentication, authorization, CSRF, validation, audit logging, and biometric data handling.

## Protected assets

- Instructor authentication data
- Student identity and attendance records
- Face images and derived face encodings
- Session cookies and CSRF tokens
- Audit history
- Course and enrollment information

## Current controls

- Passwords use Werkzeug password hashes.
- Protected routes require an authenticated instructor session.
- Instructor roles are enforced server-side from the database.
- State-changing browser requests require a CSRF token.
- Login input is validated before authentication.
- Session cookies use HttpOnly and SameSite=Lax.
- Secure cookies can be enabled with SESSION_COOKIE_SECURE=1 when HTTPS is used.
- Login/logout events are recorded in audit_logs.
- SQLAlchemy ORM is used for database access.
- Login next redirects are restricted to local application paths.
- Face recognition uses a configurable matching tolerance.
- Face image files, SQLite databases, virtual environments, and Python caches are ignored by Git.

## Biometric data rules

Face images are biometric data and must be treated as sensitive information.

- Store only the minimum images required for recognition.
- Keep dataset/known_faces/ local unless an approved transfer is required.
- Do not commit face images or generated encodings to Git.
- Do not expose face image paths or face encodings through public API responses.
- Registration images should contain one intended face only.
- Images with no detectable face must be rejected rather than silently stored.
- Images with multiple faces should be rejected because the recognition pipeline assumes one reference person.
- Keep a documented retention/deletion process for old reference images.
- When biometric enrollment is removed, delete the reference image and clear its database path.
- Face recognition alone is not a defense against deliberate spoofing; liveness/anti-spoofing is a separate control.

## Threat model summary

| Asset | Threat | Defensive control |
|---|---|---|
| Instructor account | Credential theft | Password hashing, session controls, audit log |
| Authenticated browser | CSRF | Per-session CSRF token |
| Admin endpoints | Privilege escalation | Server-side role checks |
| Student records | Injection/tampering | ORM and input validation |
| Face images | Unauthorized disclosure | Local storage, Git ignore, no public API exposure |
| Face recognition | Photo/video spoofing | Matching tolerance plus future liveness control |
| Audit records | Unauthorized access | Admin-only audit endpoint |
| Session | Cookie theft | HttpOnly, SameSite, HTTPS in production |

## Operational rules

- Never commit dataset/known_faces/, attendance.db, passwords, .env files, or private keys.
- Use HTTPS before enabling SESSION_COOKIE_SECURE=1.
- Use a unique production SECRET_KEY supplied through the environment.
- Restrict filesystem permissions for biometric datasets and database files.
- Do not copy real student biometric data into test fixtures or public repositories.

## Incident response

If biometric data or credentials are exposed:

1. Stop sharing the affected data and revoke exposed credentials.
2. Rotate the production SECRET_KEY if session integrity may be affected.
3. Identify affected accounts, images, and database records.
4. Remove exposed biometric files from unauthorized storage where possible.
5. Review audit logs for suspicious access.
6. Re-register affected biometric references when required.
7. Document the incident and follow the applicable institutional procedure.

## Next security work

1. Add liveness/anti-spoofing evaluation.
2. Add biometric registration validation and tests for zero/multiple faces.
3. Replace deprecated datetime.utcnow() with timezone-aware UTC datetimes.
4. Add security headers and production cookie configuration.
5. Define concrete biometric retention/deletion procedures.
6. Run a final dependency and secret scan before release.
