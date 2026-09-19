# Privacy Notes

## Data handled
Smart Attendance can process student names, student codes, attendance history, course enrollment, instructor account data, and face images used for recognition.

## Data minimization
- Store only fields required by the attendance workflow.
- Do not place face images or the SQLite database in Git.
- Do not put passwords, session secrets, or private keys in source control.
- Avoid logging passwords, raw face images, or face-recognition embeddings.

## Local development
The current project uses a local SQLite database and a local `dataset/` directory. These are intentionally excluded from Git through `.gitignore`.

## Retention and deletion
Retention periods are not yet implemented. Before real deployment, define who can delete biometric data, when old records are deleted, and how deletion is audited.

## Access control
The dashboard and attendance/report APIs require an authenticated instructor session. Role-based permissions are a planned next step if the application supports multiple instructor roles.

## Future review
Before production use, review consent/legal requirements applicable to biometric and student data, document the lawful purpose and retention period, and verify access permissions with the institution's requirements.
