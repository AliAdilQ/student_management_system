from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from core.test_helpers import AcademicFixture


class TeacherTests(AcademicFixture, TestCase):
    def test_name_and_future_joining_date(self):
        self.assertEqual(str(self.teacher), "Dr. Chen")
        self.teacher.joining_date = timezone.localdate() + timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.teacher.full_clean()
