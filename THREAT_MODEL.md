# Threat Model

## System boundary
Smart Attendance contains a Flask web application, SQLite database, camera/video pipeline, face-recognition service, and instructor dashboard.

## Assets
- Student identity
- Face images/embeddings
- Attendance records
- Instructor credentials and sessions
- Audit records

## Threats
| Threat | Example | Current mitigation | Next step |
|---|---|---|---|
| Credential theft | Stolen instructor password | Password hashing, session auth | Rate limiting + stronger password policy |
| Session abuse | Stolen browser cookie | HttpOnly, SameSite | HTTPS + session lifecycle review |
| Unauthorized data access | Unauthenticated dashboard/API request | Login decorators | Add role-based authorization |
| Open redirect | Crafted `next` parameter | Local-path validation | Security regression test |
| Injection | Malicious request values | SQLAlchemy ORM | Add input validation tests |
| Biometric spoofing | Printed/photo face presented to camera | None yet | Liveness/anti-spoofing research |
| Data leakage | Face dataset committed to Git | `.gitignore` | Periodic secret/data scan |
| Insider misuse | Excessive access to student data | Instructor authentication | Audit review + least privilege |

## Assumptions
- The application is operated on a trusted local network during development.
- Production deployment must use HTTPS and a properly managed secret key.
- Face data is sensitive and must not be treated like ordinary application assets.
