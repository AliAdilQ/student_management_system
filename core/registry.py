"""One definition of each module's forms, search, filters, and table columns."""

from django.contrib.auth.models import User

from academics.models import ClassGroup, Course, Department, Enrollment, Subject
from attendance.models import Attendance
from results.models import Result
from students.models import Student
from teachers.models import Teacher


def module(
    model, title, singular, icon, description, columns, search, filters=(), select=()
):
    return dict(
        model=model,
        title=title,
        singular=singular,
        icon=icon,
        description=description,
        columns=columns,
        search=search,
        filters=filters,
        select=select,
    )


MODULES = {
    "students": module(
        Student,
        "Students",
        "student",
        "people",
        "A connected view of every student's academic journey.",
        [
            ("full_name", "Student"),
            ("student_id", "Student ID"),
            ("department", "Department"),
            ("course", "Course"),
            ("semester", "Semester"),
            ("status", "Status"),
        ],
        ["first_name", "last_name", "student_id", "email"],
        ["department", "course", "gender", "status", "semester"],
        ["department", "course"],
    ),
    "teachers": module(
        Teacher,
        "Teachers",
        "teacher",
        "person-workspace",
        "The people helping your students go further.",
        [
            ("name", "Teacher"),
            ("teacher_id", "Teacher ID"),
            ("department", "Department"),
            ("specialization", "Specialization"),
            ("status", "Status"),
        ],
        ["name", "teacher_id", "email", "specialization"],
        ["department", "status"],
        ["department", "user"],
    ),
    "departments": module(
        Department,
        "Departments",
        "department",
        "buildings",
        "Organize your institution's academic departments.",
        [("name", "Department"), ("code", "Code"), ("description", "Description")],
        ["name", "code"],
    ),
    "courses": module(
        Course,
        "Courses",
        "course",
        "journal-bookmark",
        "Programs designed for the next generation.",
        [
            ("name", "Course"),
            ("code", "Code"),
            ("department", "Department"),
            ("duration", "Years"),
        ],
        ["name", "code", "department__name"],
        ["department"],
        ["department"],
    ),
    "subjects": module(
        Subject,
        "Subjects",
        "subject",
        "book",
        "Build a clear curriculum, one subject at a time.",
        [
            ("name", "Subject"),
            ("code", "Code"),
            ("course", "Course"),
            ("teacher", "Teacher"),
            ("semester", "Semester"),
            ("credit_hours", "Credits"),
        ],
        ["name", "code", "teacher__name"],
        ["course", "teacher", "semester"],
        ["course", "teacher"],
    ),
    "classes": module(
        ClassGroup,
        "Classes",
        "class",
        "grid",
        "Keep classes, rooms, and teaching schedules connected.",
        [
            ("name", "Class"),
            ("subject", "Subject"),
            ("room", "Room"),
            ("schedule", "Schedule"),
            ("capacity", "Capacity"),
        ],
        ["name", "room", "subject__name"],
        ["subject"],
        ["subject"],
    ),
    "enrollments": module(
        Enrollment,
        "Enrollments",
        "enrollment",
        "person-check",
        "Manage course registrations and academic terms.",
        [
            ("student", "Student"),
            ("course", "Course"),
            ("semester", "Semester"),
            ("academic_year", "Academic year"),
            ("enrollment_date", "Enrolled"),
            ("status", "Status"),
        ],
        [
            "student__first_name",
            "student__last_name",
            "student__student_id",
            "course__name",
            "academic_year",
        ],
        ["course", "status", "semester"],
        ["student", "course"],
    ),
    "attendance": module(
        Attendance,
        "Attendance",
        "attendance record",
        "calendar-check",
        "Every day counts. Keep a reliable attendance record.",
        [
            ("student", "Student"),
            ("subject", "Subject"),
            ("date", "Date"),
            ("class_group", "Class"),
            ("status", "Status"),
        ],
        [
            "student__first_name",
            "student__last_name",
            "student__student_id",
            "subject__name",
        ],
        ["student", "subject", "date", "status"],
        ["student", "subject", "class_group"],
    ),
    "results": module(
        Result,
        "Results & grades",
        "result",
        "bar-chart",
        "Turn assessment records into meaningful progress.",
        [
            ("student", "Student"),
            ("subject", "Subject"),
            ("exam_type", "Assessment"),
            ("exam_date", "Date"),
            ("marks_obtained", "Marks"),
            ("percentage", "Score %"),
            ("grade", "Grade"),
        ],
        [
            "student__first_name",
            "student__last_name",
            "student__student_id",
            "subject__name",
        ],
        ["student", "subject", "exam_type"],
        ["student", "subject"],
    ),
    "accounts": module(
        User,
        "User accounts",
        "account",
        "shield-lock",
        "Give your team the right access to the right tools.",
        [
            ("username", "Username"),
            ("first_name", "First name"),
            ("last_name", "Last name"),
            ("email", "Email"),
            ("is_active", "Active"),
            ("is_superuser", "Superuser"),
        ],
        ["username", "first_name", "last_name", "email"],
        ["is_active"],
    ),
}
