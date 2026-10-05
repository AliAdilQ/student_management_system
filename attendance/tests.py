from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from academics.models import Course, Subject
from core.test_helpers import AcademicFixture

from .models import Attendance


class AttendanceTests(AcademicFixture, TestCase):
    def setUp(self):
        self.client.force_login(self.admin)

    def test_create_and_student_attendance_rate(self):
        payload = {
            "student": self.student.pk,
            "subject": self.subject.pk,
            "date": str(timezone.localdate()),
            "status": "present",
        }
        self.assertRedirects(
            self.client.post("/attendance/add/", payload), "/attendance/"
        )
        Attendance.objects.create(
            student=self.student,
            subject=self.subject,
            date=timezone.localdate() - timedelta(days=1),
            status="absent",
        )
        self.assertEqual(self.student.attendance_rate, 50)
        self.assertContains(
            self.client.get(f"/attendance/?student={self.student.pk}"), "Olivia"
        )

    def test_daily_duplicate_constraint(self):
        Attendance.objects.create(
            student=self.student, subject=self.subject, date=timezone.localdate()
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Attendance.objects.create(
                student=self.student, subject=self.subject, date=timezone.localdate()
            )

    def test_future_and_wrong_course_rejected(self):
        record = Attendance(
            student=self.student,
            subject=self.subject,
            date=timezone.localdate() + timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            record.full_clean()
        other = Course.objects.create(
            name="Other", code="OTHER", department=self.department
        )
        record.date = timezone.localdate()
        record.subject = Subject.objects.create(
            name="Other", code="OTHER1", course=other
        )
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_bulk_register_renders_and_upserts(self):
        payload = {
            "subject": self.subject.pk,
            "class_group": self.class_group.pk,
            "date": str(timezone.localdate()),
        }
        response = self.client.get("/attendance/register/", payload)
        self.assertContains(response, "status_" + str(self.student.pk))
        self.assertContains(response, "Absent")
        self.assertEqual(
            self.client.post(
                "/attendance/register/",
                {**payload, f"status_{self.student.pk}": "late"},
            ).status_code,
            302,
        )
        self.assertEqual(Attendance.objects.get().status, "late")
        self.assertEqual(self.student.attendance_rate, 100)
        self.client.post(
            "/attendance/register/", {**payload, f"status_{self.student.pk}": "absent"}
        )
        self.assertEqual(Attendance.objects.count(), 1)
        self.assertEqual(Attendance.objects.get().status, "absent")

    def test_bulk_invalid_status_is_atomic(self):
        response = self.client.post(
            "/attendance/register/",
            {
                "subject": self.subject.pk,
                "date": str(timezone.localdate()),
                f"status_{self.student.pk}": "invalid",
            },
        )
        self.assertContains(response, "Select Present, Absent, or Late")
        self.assertEqual(Attendance.objects.count(), 0)
