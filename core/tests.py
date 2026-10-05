from io import StringIO

from django.contrib.auth.models import Group, Permission, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from academics.models import ClassGroup, Course, Department, Enrollment, Subject
from attendance.models import Attendance
from results.models import Result
from students.models import Student
from teachers.models import Teacher

from .registry import MODULES
from .test_helpers import AcademicFixture


class AccessTests(AcademicFixture, TestCase):
    def test_anonymous_routes_require_login(self):
        for path in [
            "/",
            "/profile/",
            "/students/",
            "/attendance/register/",
            "/results/",
            "/accounts/",
        ]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/login/?next=", response.url)

    def test_login_and_post_logout(self):
        response = self.client.post(
            "/login/", {"username": "admin", "password": "TestPassword@2026"}
        )
        self.assertRedirects(response, "/")
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertRedirects(self.client.post("/logout/"), "/login/")

    def test_invalid_login_message(self):
        response = self.client.post(
            "/login/", {"username": "admin", "password": "wrong"}
        )
        self.assertContains(response, "username or password is incorrect")

    def test_viewer_cannot_write_or_manage_accounts(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get("/students/").status_code, 200)
        for path in [
            "/students/add/",
            f"/students/{self.student.pk}/edit/",
            f"/students/{self.student.pk}/delete/",
            "/attendance/register/",
            "/accounts/",
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)
                self.assertEqual(self.client.post(path, {}).status_code, 403)

    def test_specific_permission_allows_only_that_action(self):
        self.viewer.user_permissions.add(
            Permission.objects.get(codename="add_attendance")
        )
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get("/attendance/add/").status_code, 200)
        self.assertEqual(self.client.get("/students/add/").status_code, 403)

    def test_csrf_rejects_write_without_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertContains(
            client.post("/students/add/", self.student_payload()),
            "Your form session needs a refresh",
            status_code=403,
        )

    def test_external_next_url_is_rejected(self):
        response = self.client.post(
            "/login/?next=https://malicious.example/",
            {"username": "admin", "password": "TestPassword@2026"},
        )
        self.assertEqual(response.url, "/")

    def test_all_modules_and_admin_render(self):
        self.client.force_login(self.admin)
        for module, config in MODULES.items():
            with self.subTest(module=module):
                self.assertEqual(
                    self.client.get(
                        reverse("record-list", kwargs={"module": module})
                    ).status_code,
                    200,
                )
                self.assertEqual(
                    self.client.get(
                        reverse("record-add", kwargs={"module": module})
                    ).status_code,
                    200,
                )
        self.assertContains(self.client.get("/admin/"), "Institution administration")
        self.assertContains(self.client.get("/"), "dashboard-data")

    def test_password_change_keeps_session(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/password/change/",
            {
                "old_password": "TestPassword@2026",
                "new_password1": "ChangedStrong@2026",
                "new_password2": "ChangedStrong@2026",
            },
        )
        self.assertRedirects(response, "/profile/")
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("ChangedStrong@2026"))
        self.assertEqual(self.client.get("/").status_code, 200)

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False)
    def test_friendly_error_pages(self):
        self.assertContains(
            self.client.get("/missing/module/route/"),
            "A little off campus",
            status_code=404,
        )
        self.client.force_login(self.viewer)
        self.assertContains(
            self.client.get("/students/add/"), "needs permission", status_code=403
        )

    def test_cannot_delete_self_or_deactivate_last_superuser(self):
        self.client.force_login(self.admin)
        self.client.post(f"/accounts/{self.admin.pk}/delete/")
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())
        response = self.client.post(
            f"/accounts/{self.admin.pk}/edit/",
            {"username": "admin", "email": "admin@example.com", "role": ""},
        )
        self.assertContains(response, "At least one active superuser")
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)


class SeedTests(TestCase):
    @override_settings(DEBUG=True)
    def test_seed_is_idempotent_and_preserves_password(self):
        models = [
            Student,
            Teacher,
            Department,
            Course,
            Subject,
            ClassGroup,
            Enrollment,
            Attendance,
            Result,
        ]
        call_command("seed_data", stdout=StringIO())
        counts = [model.objects.count() for model in models]
        self.assertGreaterEqual(counts[0], 20)
        self.assertEqual(counts[1:5], [5, 3, 6, 13])
        admin = User.objects.get(username="admin")
        self.assertTrue(admin.check_password("Admin@12345"))
        admin.set_password("ChangedPassword@123")
        admin.save()
        call_command("seed_data", stdout=StringIO())
        self.assertEqual(counts, [model.objects.count() for model in models])
        admin.refresh_from_db()
        self.assertTrue(admin.check_password("ChangedPassword@123"))
        for model in models:
            for obj in model.objects.all():
                obj.full_clean()
        self.assertEqual(Group.objects.count(), 3)

    @override_settings(DEBUG=False)
    def test_seed_blocked_in_production(self):
        with self.assertRaises(CommandError):
            call_command("seed_data", stdout=StringIO())


class CrudTests(AcademicFixture, TestCase):
    def test_related_modules_create_update_and_delete(self):
        self.client.force_login(self.admin)
        specs = [
            (
                "departments",
                Department,
                {"name": "Arts", "code": "ART", "description": "Creative studies"},
                {"name": "Fine Arts"},
            ),
            (
                "teachers",
                Teacher,
                {
                    "teacher_id": "T002",
                    "name": "Dr. Smith",
                    "email": "smith@example.com",
                    "department": self.department.pk,
                    "specialization": "Math",
                    "joining_date": "2020-01-01",
                    "status": "active",
                },
                {"name": "Dr. Jane Smith"},
            ),
            (
                "courses",
                Course,
                {
                    "name": "Data Science",
                    "code": "DS",
                    "department": self.department.pk,
                    "duration": 4,
                },
                {"name": "Applied Data Science"},
            ),
            (
                "subjects",
                Subject,
                {
                    "name": "Statistics",
                    "code": "ST101",
                    "course": self.course.pk,
                    "teacher": self.teacher.pk,
                    "credit_hours": 3,
                    "semester": 1,
                },
                {"name": "Applied Statistics"},
            ),
            (
                "classes",
                ClassGroup,
                {
                    "name": "Section B",
                    "subject": self.subject.pk,
                    "room": "202",
                    "schedule": "Tuesday 10:00",
                    "capacity": 30,
                },
                {"room": "203"},
            ),
            (
                "enrollments",
                Enrollment,
                {
                    "student": self.student.pk,
                    "course": self.course.pk,
                    "semester": 1,
                    "academic_year": "2026-2027",
                    "enrollment_date": "2026-01-01",
                    "status": "active",
                    "subjects": [self.subject.pk],
                },
                {"status": "inactive"},
            ),
            (
                "results",
                Result,
                {
                    "student": self.student.pk,
                    "subject": self.subject.pk,
                    "exam_type": "midterm",
                    "exam_date": "2026-01-01",
                    "marks_obtained": 81,
                    "total_marks": 100,
                },
                {"marks_obtained": 90},
            ),
        ]
        for module, model, payload, update in specs:
            with self.subTest(module=module):
                before = model.objects.count()
                response = self.client.post(f"/{module}/add/", payload)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(model.objects.count(), before + 1)
                obj = model.objects.latest("pk")
                for action in ["", "edit/", "delete/"]:
                    self.assertEqual(
                        self.client.get(f"/{module}/{obj.pk}/{action}").status_code, 200
                    )
                self.assertEqual(
                    self.client.post(
                        f"/{module}/{obj.pk}/edit/", {**payload, **update}
                    ).status_code,
                    302,
                )
                obj.refresh_from_db()
                for key, value in update.items():
                    self.assertEqual(getattr(obj, key), value)
                self.assertEqual(
                    self.client.post(f"/{module}/{obj.pk}/delete/").status_code, 302
                )
                self.assertEqual(model.objects.count(), before)

    @override_settings(DEBUG=True)
    def test_account_creation_role_and_password(self):
        call_command("seed_data", stdout=StringIO())
        self.client.force_login(self.admin)
        role = Group.objects.get(name="Faculty")
        response = self.client.post(
            "/accounts/add/",
            {
                "username": "faculty",
                "first_name": "Jane",
                "email": "jane@example.com",
                "role": role.pk,
                "is_active": "on",
                "password1": "FacultyStrong@2026",
                "password2": "FacultyStrong@2026",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="faculty")
        self.assertTrue(user.check_password("FacultyStrong@2026"))
        self.assertTrue(user.has_perm("attendance.add_attendance"))
        self.assertFalse(user.has_perm("students.add_student"))
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["Faculty"])
