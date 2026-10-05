from datetime import date

from django.contrib.auth.models import User
from django.utils import timezone

from academics.models import ClassGroup, Course, Department, Subject
from students.models import Student
from teachers.models import Teacher


class AcademicFixture:
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            "admin", "admin@example.com", "TestPassword@2026"
        )
        cls.viewer = User.objects.create_user("viewer", password="TestPassword@2026")
        cls.department = Department.objects.create(name="Computer Science", code="CS")
        cls.course = Course.objects.create(
            name="Computer Science", code="BSCS", department=cls.department
        )
        cls.teacher = Teacher.objects.create(
            name="Dr. Chen",
            teacher_id="T001",
            email="chen@example.com",
            department=cls.department,
            specialization="AI",
        )
        cls.subject = Subject.objects.create(
            name="Programming", code="CS101", course=cls.course, teacher=cls.teacher
        )
        cls.class_group = ClassGroup.objects.create(
            name="A", subject=cls.subject, room="101", schedule="Monday 09:00"
        )
        cls.student = Student.objects.create(
            student_id="S001",
            first_name="Olivia",
            last_name="Bennett",
            email="olivia@example.com",
            gender="female",
            date_of_birth=date(2004, 2, 2),
            department=cls.department,
            course=cls.course,
        )

    def student_payload(self, **overrides):
        return {
            "student_id": "S002",
            "first_name": "James",
            "last_name": "Lee",
            "email": "james@example.com",
            "phone": "",
            "gender": "male",
            "date_of_birth": "2005-01-02",
            "address": "Campus Road",
            "department": self.department.pk,
            "course": self.course.pk,
            "semester": 1,
            "admission_date": str(timezone.localdate()),
            "status": "active",
            **overrides,
        }
