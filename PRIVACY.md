# Privacy & Biometric Data Handling

## Scope

Smart Attendance processes student identity and facial biometric data for classroom attendance. This document describes the current local-system handling and the controls implemented in v2.

## Data handled

- Student ID/code and full name.
- Course enrollment and attendance events.
- Current attendance state and timestamps.
- Instructor account username, display name, password hash, and role.
- Security audit events such as login/logout.
- A reference face image and its derived 128-dimensional face encoding.

Plain-text passwords are never stored. Passwords are verified against a password hash.

## Purpose

Biometric data is used only to identify enrolled students for attendance. It should not be reused for unrelated purposes without an appropriate authorization and privacy review.

## Biometric flow

1. A reference image is registered for an enrolled student.
2. Registration validates that the image contains exactly one detectable face.
3. The application derives a face encoding for matching.
4. Live camera frames are compared against the loaded reference encodings.
5. A match is accepted only when the configured face-distance tolerance is met.

The current recognition pipeline does not provide liveness detection and therefore should not be treated as proof that a live person is present.

## Access control

- Student attendance and report APIs require an authenticated instructor.
- Admin audit data requires the ADMIN role.
- Authorization is checked against the database role rather than trusting a client-controlled session role.
- State-changing requests are protected by CSRF validation.
- Security-sensitive login/logout events are recorded without passwords or face data.

## Storage and retention

Reference images live under the local dataset directory and are excluded from Git by .gitignore.

For a production deployment, the operator must define and enforce a documented retention period for:
- reference face images;
- derived biometric encodings;
- attendance history;
- audit logs;
- backups.

Deletion should remove both the database reference and the corresponding biometric file and backup copies when retention expires.

## Incident response

If biometric data or credentials are suspected to be exposed:

1. Restrict access to the affected system.
2. Rotate credentials and the production secret key where appropriate.
3. Preserve relevant security audit evidence.
4. Identify affected records and storage locations.
5. Remove unauthorized copies where possible.
6. Document the incident and follow the organization's applicable privacy and security process.

## Known limitations

- No liveness or anti-spoofing model is implemented.
- Face recognition accuracy depends on image quality, lighting, pose, and the selected tolerance.
- A reference image with zero or multiple faces is rejected by registration.
- The current application is designed as a local or academic system; production deployment requires an infrastructure and privacy review.
