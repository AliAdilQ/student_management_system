from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from core.test_helpers import AcademicFixture

from .models import Result


class ResultTests(AcademicFixture, TestCase):
    def result(self, marks, total=100):
        return Result(
            student=self.student,
            subject=self.subject,
            exam_type="final",
            exam_date=date(2026, 1, 1),
            marks_obtained=Decimal(str(marks)),
            total_marks=Decimal(str(total)),
        )

    def test_every_grade_boundary(self):
        for marks, grade in [
            (100, "A+"),
            (90, "A+"),
            (89.99, "A"),
            (80, "A"),
            (79.99, "B"),
            (70, "B"),
            (60, "C"),
            (50, "D"),
            (49.99, "F"),
            (0, "F"),
        ]:
            with self.subTest(marks=marks):
                result = self.result(marks)
                result.full_clean()
                self.assertEqual(result.grade, grade)
                self.assertEqual(result.percentage, Decimal(str(marks)))

    def test_scaled_marks_and_rounding(self):
        self.assertEqual(self.result(45, 50).percentage, 90)
        self.assertEqual(self.result(1, 3).percentage, Decimal("33.33"))
        self.assertEqual(self.result(89.999).grade, "A")

    def test_invalid_marks_rejected(self):
        for marks, total in [(101, 100), (-1, 100), (0, 0)]:
            with (
                self.subTest(marks=marks, total=total),
                self.assertRaises(ValidationError),
            ):
                self.result(marks, total).full_clean()

    def test_form_validation_and_grade_display(self):
        self.client.force_login(self.admin)
        payload = {
            "student": self.student.pk,
            "subject": self.subject.pk,
            "exam_type": "final",
            "exam_date": "2026-01-01",
            "marks_obtained": 105,
            "total_marks": 100,
        }
        self.assertContains(
            self.client.post("/results/add/", payload), "cannot exceed total marks"
        )
        self.assertEqual(
            self.client.post(
                "/results/add/", {**payload, "marks_obtained": 95}
            ).status_code,
            302,
        )
        self.assertContains(self.client.get("/results/"), "A+")
