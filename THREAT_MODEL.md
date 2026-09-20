# Biometric Threat Model

## Assets

- Student reference face images
- Face encodings held in application memory
- Student identity and attendance records
- Instructor credentials and sessions

## Threats

### T1 — Unauthorized access to face images

An attacker who obtains the dataset could use the images outside the attendance system.

Controls:
- Keep the dataset local.
- Do not commit it to Git.
- Restrict filesystem permissions.
- Avoid returning image files or paths from public APIs.

### T2 — Presentation attack / spoofing

A person may present a photograph or replayed video of another student.

Current control:
- Face matching tolerance is deliberately stricter than the library default.

Limitation:
- Matching tolerance does not prove liveness.

Planned control:
- Evaluate liveness or anti-spoofing before relying on the system for high-assurance attendance.

### T3 — Bad reference image

A reference image may contain no face or more than one face.

Controls:
- Registration should validate that exactly one face is detectable.
- Reject ambiguous images rather than selecting an arbitrary face.

### T4 — Credential compromise

A compromised instructor account could expose student records and audit data.

Controls:
- Password hashing.
- CSRF protection.
- Server-side RBAC.
- Audit logging.
- Session cookie protections.

### T5 — Data retention

Old biometric images may remain after a student no longer needs recognition.

Control needed:
- Define retention and deletion rules with the institution/course owner.

## Risk boundary

This project is a defensive academic attendance system. Face recognition is an identification aid, not a guarantee of identity or liveness.

Any production deployment should define who may access biometric data, why it is collected, how long it is retained, and how deletion requests are handled.
