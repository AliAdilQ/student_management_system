from datetime import date

from django.core.exceptions import ValidationError
from django.forms import modelform_factory
from django.test import TestCase

from core.forms import RecordForm
from core.test_helpers import AcademicFixture

from .models import Course, Enrollment, Subject


class AcademicTests(AcademicFixture, TestCase):
    def test_enrollment_academic_year_and_course_validation(self):
        record = Enrollment(
            student=self.student,
            course=self.course,
            semester=1,
            academic_year="2026-2029",
            enrollment_date=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            record.full_clean()
        record.academic_year = "2026-2027"
        record.course = Course.objects.create(
            name="Other", code="OTHER", department=self.department
        )
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_enrollment_subjects_match_course_and_semester(self):
        other = Subject.objects.create(
            name="Advanced", code="ADV", course=self.course, semester=3
        )
        cls = modelform_factory(Enrollment, form=RecordForm, exclude=[])
        form = cls(
            {
                "student": self.student.pk,
                "course": self.course.pk,
                "semester": 1,
                "academic_year": "2026-2027",
                "enrollment_date": "2026-01-01",
                "status": "active",
                "subjects": [other.pk],
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("subjects", form.errors)

    def test_linked_student_course_change_is_rejected(self):
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            semester=1,
            academic_year="2026-2027",
        )
        self.student.course = Course.objects.create(
            name="Other", code="OTHER", department=self.department
        )
        with self.assertRaises(ValidationError):
            self.student.full_clean()

    def test_linked_course_department_and_duration_changes_are_rejected(self):
        from .models import Department

        other = Department.objects.create(name="Business", code="BA")
        self.course.department = other
        with self.assertRaises(ValidationError):
            self.course.full_clean()
        self.course.department = self.department
        self.student.semester = 3
        self.student.save()
        self.course.duration = 1
        with self.assertRaises(ValidationError):
            self.course.full_clean()

    def test_linked_subject_and_class_changes_are_rejected(self):
        from attendance.models import Attendance

        Attendance.objects.create(
            student=self.student, subject=self.subject, class_group=self.class_group
        )
        self.subject.semester = 3
        with self.assertRaises(ValidationError):
            self.subject.full_clean()
        other = Subject.objects.create(name="Networks", code="NET", course=self.course)
        self.class_group.subject = other
        with self.assertRaises(ValidationError):
            self.class_group.full_clean()
