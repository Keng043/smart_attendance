from datetime import datetime, timedelta

from app.attendance_controller import AttendanceController
from app.models import Student, Course, Enrollment, StudentState, StateEnum, AttendanceLog, AlertLog


class FakeSession:
    def __init__(self):
        self.students, self.courses, self.enrollments = [], [], []
        self.states, self.attendance, self.alerts = [], [], []
        self.commits = 0

    def add(self, obj):
        if isinstance(obj, StudentState): self.states.append(obj)
        elif isinstance(obj, AttendanceLog): self.attendance.append(obj)
        elif isinstance(obj, AlertLog): self.alerts.append(obj)

    def flush(self):
        for state in self.states:
            if getattr(state, "id", None) is None: state.id = len(self.states)

    def commit(self): self.commits += 1
    def close(self): pass
    def query(self, model): return FakeQuery(self, model)


class FakeQuery:
    def __init__(self, db, model):
        self.db, self.model, self.filters = db, model, {}

    def filter_by(self, **kwargs):
        self.filters.update(kwargs)
        return self

    def first(self):
        rows = self.all()
        return rows[0] if rows else None

    def all(self):
        data = {
            Student: self.db.students,
            Course: self.db.courses,
            Enrollment: self.db.enrollments,
            StudentState: self.db.states,
            AttendanceLog: self.db.attendance,
        }.get(self.model, [])
        return [x for x in data if all(getattr(x, k, None) == v for k, v in self.filters.items())]


class FakeSchedule:
    def __init__(self, course_id=1): self.course_id = course_id
    def get_active_course(self, now=None): return {"id": self.course_id}


def make_controller():
    db = FakeSession()
    return AttendanceController(lambda: db, FakeSchedule()), db


def test_first_detection_checks_in_enrolled_student():
    controller, db = make_controller()
    db.students.append(Student(id=1, student_code="S001", full_name="Test Student"))
    db.courses.append(Course(id=1, course_code="CS", course_name="Test"))
    db.enrollments.append(Enrollment(student_id=1, course_id=1))

    result = controller.handle_face_detected(1, datetime.utcnow())

    assert result["success"] is True
    assert len(db.attendance) == 1
    assert db.states[0].current_state == StateEnum.IN_CLASS


def test_unenrolled_student_is_rejected():
    controller, db = make_controller()
    db.students.append(Student(id=1, student_code="S001", full_name="Test Student"))

    result = controller.handle_face_detected(1, datetime.utcnow())

    assert result["success"] is False
    assert "ไม่ได้ลงทะเบียน" in result["message"]
    assert db.attendance == []


def test_away_student_returns_without_duplicate_attendance():
    controller, db = make_controller()
    db.students.append(Student(id=1, student_code="S001", full_name="Test Student"))
    db.enrollments.append(Enrollment(student_id=1, course_id=1))
    db.attendance.append(AttendanceLog(student_id=1, course_id=1))
    db.states.append(StudentState(
        student_id=1, current_state=StateEnum.AWAY, state_changed_at=datetime.utcnow()
    ))

    result = controller.handle_face_detected(1, datetime.utcnow())

    assert result["success"] is True
    assert len(db.attendance) == 1
    assert db.states[0].current_state == StateEnum.IN_CLASS


def test_timeout_marks_missing_and_creates_alert():
    controller, db = make_controller()
    old = datetime.utcnow() - timedelta(minutes=20)
    student = Student(id=1, student_code="S001", full_name="Test Student")
    db.students.append(student)
    state = StudentState(
        student_id=1, current_state=StateEnum.AWAY, state_changed_at=old
    )
    state.student = student
    db.states.append(state)

    missing = controller.check_and_flag_missing_students()

    assert missing == ["Test Student"]
    assert db.states[0].current_state == StateEnum.MISSING
    assert len(db.alerts) == 1
