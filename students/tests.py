from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from academics.models import Department
from core.test_helpers import AcademicFixture

from .models import Student


class StudentTests(AcademicFixture, TestCase):
    def setUp(self):
        self.client.force_login(self.admin)

    def test_create_list_search_filter_and_detail(self):
        self.assertRedirects(
            self.client.post("/students/add/", self.student_payload()), "/students/"
        )
        student = Student.objects.get(student_id="S002")
        self.assertEqual(student.full_name, "James Lee")
        self.assertEqual(student.initials, "JL")
        self.assertEqual(student.year, 1)
        self.assertContains(self.client.get("/students/?q=James"), "James Lee")
        self.assertNotContains(self.client.get("/students/?q=James"), "Olivia Bennett")
        self.assertContains(
            self.client.get(
                f"/students/?department={self.department.pk}&sort=-student_id"
            ),
            "James Lee",
        )
        self.assertContains(self.client.get(f"/students/{student.pk}/"), "James Lee")

    def test_update_and_confirm_delete(self):
        response = self.client.post(
            f"/students/{self.student.pk}/edit/",
            self.student_payload(
                student_id="S001",
                email="olivia@example.com",
                first_name="Olivia",
                last_name="Updated",
            ),
        )
        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.last_name, "Updated")
        self.client.get(f"/students/{self.student.pk}/delete/")
        self.assertTrue(Student.objects.filter(pk=self.student.pk).exists())
        self.assertRedirects(
            self.client.post(f"/students/{self.student.pk}/delete/"), "/students/"
        )
        self.assertFalse(Student.objects.filter(pk=self.student.pk).exists())

    def test_course_department_mismatch_and_duplicate_email(self):
        other = Department.objects.create(name="Business", code="BA")
        response = self.client.post(
            "/students/add/", self.student_payload(department=other.pk)
        )
        self.assertContains(response, "must belong to the department")
        response = self.client.post(
            "/students/add/", self.student_payload(email="olivia@example.com")
        )
        self.assertContains(response, "already exists")
        self.assertEqual(Student.objects.count(), 1)

    def test_invalid_dates_and_semester(self):
        self.student.date_of_birth = timezone.localdate() + timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.student.full_clean()
        response = self.client.post("/students/add/", self.student_payload(semester=9))
        self.assertContains(response, "exceeds this course")

    def test_pagination_and_xss_escaping(self):
        for index in range(12):
            Student.objects.create(
                **{
                    **{
                        key: value
                        for key, value in self.student_payload().items()
                        if key not in ["department", "course"]
                    },
                    "student_id": f"P{index}",
                    "email": f"p{index}@example.com",
                    "first_name": "<script>alert(1)</script>"
                    if index == 0
                    else f"Student{index}",
                    "department": self.department,
                    "course": self.course,
                }
            )
        response = self.client.get("/students/")
        self.assertEqual(len(response.context["object_list"]), 10)
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertEqual(
            len(self.client.get("/students/?page=2").context["object_list"]), 3
        )

    def test_protected_department_delete_is_friendly(self):
        response = self.client.post(
            f"/departments/{self.department.pk}/delete/", follow=True
        )
        self.assertContains(response, "linked academic data")
        self.assertTrue(Department.objects.filter(pk=self.department.pk).exists())

    def test_photo_accepts_valid_image_and_rejects_invalid_or_oversized_files(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.forms import modelform_factory
        from PIL import Image

        from core.forms import RecordForm

        buffer = BytesIO()
        Image.new("RGB", (20, 20), "purple").save(buffer, format="PNG")
        image = buffer.getvalue()
        cls = modelform_factory(Student, form=RecordForm, exclude=[])
        valid = cls(
            self.student_payload(),
            {
                "photo": SimpleUploadedFile(
                    "avatar.png", image, content_type="image/png"
                )
            },
        )
        self.assertTrue(valid.is_valid(), valid.errors)
        invalid = cls(
            self.student_payload(),
            {
                "photo": SimpleUploadedFile(
                    "avatar.png", b"invalid image", content_type="image/png"
                )
            },
        )
        self.assertFalse(invalid.is_valid())
        self.assertIn("photo", invalid.errors)
        oversized = cls(
            self.student_payload(),
            {
                "photo": SimpleUploadedFile(
                    "avatar.png",
                    image + b"x" * (2 * 1024 * 1024),
                    content_type="image/png",
                )
            },
        )
        self.assertFalse(oversized.is_valid())
        self.assertIn("smaller than 2 MB", str(oversized.errors))
