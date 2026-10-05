"""Deterministic, additive local demo data; existing accounts are never reset."""

import random
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from academics.models import ClassGroup, Course, Department, Enrollment, Subject
from attendance.models import Attendance
from results.models import Result
from students.models import Student
from teachers.models import Teacher


class Command(BaseCommand):
    help = "Create local demo data and permission groups without duplicating or overwriting existing records."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Demo seeding is disabled when DEBUG=False. Create real accounts with createsuperuser."
            )
        rng = random.Random(42)
        today = timezone.localdate()
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "first_name": "Alex",
                "last_name": "Morgan",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password("Admin@12345")
            admin.save()
        elif not admin.is_superuser:
            self.stdout.write(
                self.style.WARNING(
                    "Existing 'admin' account preserved; it was not promoted or its password reset."
                )
            )
        app_labels = ["academics", "students", "teachers", "attendance", "results"]
        registrar, _ = Group.objects.get_or_create(name="Registrar")
        faculty, _ = Group.objects.get_or_create(name="Faculty")
        viewer, _ = Group.objects.get_or_create(name="Viewer")
        permissions = Permission.objects.filter(content_type__app_label__in=app_labels)
        registrar.permissions.set(permissions)
        viewer.permissions.set(permissions.filter(codename__startswith="view_"))
        faculty.permissions.set(
            permissions.filter(codename__startswith="view_")
            | permissions.filter(
                content_type__app_label__in=["attendance", "results"]
            ).exclude(codename__startswith="delete_")
        )
        department_specs = [
            (
                "CS",
                "Computer Science",
                "Computing, intelligent systems, and software innovation.",
            ),
            (
                "BA",
                "Business Administration",
                "Developing thoughtful leaders and entrepreneurs.",
            ),
            (
                "IT",
                "Information Technology",
                "Connecting people, networks, and digital infrastructure.",
            ),
        ]
        departments = [
            Department.objects.get_or_create(
                code=code, defaults={"name": name, "description": description}
            )[0]
            for code, name, description in department_specs
        ]
        course_specs = [
            ("BSCS", "BS Computer Science", 0),
            ("BBA", "BBA", 1),
            ("BSIT", "BS Information Technology", 2),
            ("BSDS", "Data Science", 0),
            ("BSSE", "Software Engineering", 0),
            ("BSAI", "Artificial Intelligence", 2),
        ]
        courses = [
            Course.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "department": departments[dept],
                    "duration": 4,
                    "description": f"A four-year program in {name.lower()} with practical learning and a final-year capstone.",
                },
            )[0]
            for code, name, dept in course_specs
        ]
        teacher_specs = [
            ("Dr. Sarah Mitchell", "Algorithms & computation", 0),
            ("Prof. James Wilson", "Business strategy", 1),
            ("Dr. Aisha Rahman", "Networks & security", 2),
            ("Dr. Daniel Chen", "Machine learning", 0),
            ("Prof. Elena Garcia", "Software architecture", 0),
        ]
        teachers = [
            Teacher.objects.get_or_create(
                teacher_id=f"FAC-{i + 1:03d}",
                defaults={
                    "name": name,
                    "email": f"faculty{i + 1}@example.com",
                    "phone": f"+1 202 555 {1100 + i}",
                    "department": departments[dept],
                    "specialization": specialty,
                    "joining_date": date(2020 + i % 3, 8, 15),
                },
            )[0]
            for i, (name, specialty, dept) in enumerate(teacher_specs)
        ]
        subject_specs = [
            ("Programming Fundamentals", 0, 0, 1),
            ("Data Structures", 0, 0, 3),
            ("Database Systems", 0, 4, 3),
            ("Principles of Management", 1, 1, 1),
            ("Business Statistics", 1, 1, 3),
            ("Computer Networks", 2, 2, 1),
            ("Operating Systems", 2, 2, 3),
            ("Statistics", 3, 3, 1),
            ("Machine Learning", 3, 3, 3),
            ("Web Development", 4, 4, 1),
            ("Software Engineering", 4, 4, 3),
            ("Artificial Intelligence", 5, 3, 1),
            ("Deep Learning", 5, 3, 3),
        ]
        subjects = [
            Subject.objects.get_or_create(
                code=f"{courses[course].code}-{100 + i}",
                defaults={
                    "name": name,
                    "course": courses[course],
                    "teacher": teachers[teacher],
                    "credit_hours": 3 if i % 3 else 4,
                    "semester": semester,
                },
            )[0]
            for i, (name, course, teacher, semester) in enumerate(subject_specs)
        ]
        classes = {
            subject.pk: ClassGroup.objects.get_or_create(
                name="Section A",
                subject=subject,
                defaults={
                    "room": f"Hall {100 + i}",
                    "schedule": "Monday & Wednesday, 09:00–10:30",
                    "capacity": 35,
                },
            )[0]
            for i, subject in enumerate(subjects)
        }
        names = [
            ("Olivia", "Bennett", "female"),
            ("Liam", "Anderson", "male"),
            ("Emma", "Williams", "female"),
            ("Noah", "Thompson", "male"),
            ("Amelia", "Davis", "female"),
            ("Ethan", "Martinez", "male"),
            ("Sophia", "Patel", "female"),
            ("Lucas", "Garcia", "male"),
            ("Isabella", "Chen", "female"),
            ("Mason", "Robinson", "male"),
            ("Mia", "Wilson", "female"),
            ("James", "Taylor", "male"),
            ("Charlotte", "Lee", "female"),
            ("Benjamin", "Clark", "male"),
            ("Harper", "Lewis", "female"),
            ("Henry", "Walker", "male"),
            ("Aria", "Rahman", "female"),
            ("Alexander", "Hall", "male"),
            ("Evelyn", "Young", "female"),
            ("Daniel", "Scott", "male"),
            ("Riley", "Morgan", "other"),
            ("Zoe", "Adams", "female"),
            ("Samuel", "Green", "male"),
            ("Grace", "Turner", "female"),
        ]
        for i, (first, last, gender) in enumerate(names):
            course = courses[i % len(courses)]
            semester = 1 if i < 12 else 3
            student, _ = Student.objects.get_or_create(
                student_id=f"STU-2026-{i + 1:03d}",
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": f"{first.lower()}.{last.lower()}@example.com",
                    "phone": f"+1 202 555 {1200 + i}",
                    "gender": gender,
                    "date_of_birth": date(2003 + i % 4, i % 12 + 1, 10 + i % 15),
                    "address": f"{120 + i} University Avenue, Riverside",
                    "department": course.department,
                    "course": course,
                    "semester": semester,
                    "admission_date": today
                    - timedelta(days=45 + (semester // 2) * 365),
                    "status": "inactive" if i == 19 else "active",
                },
            )
            enrollment, new = Enrollment.objects.get_or_create(
                student=student,
                course=student.course,
                semester=student.semester,
                academic_year=f"{today.year}-{today.year + 1}",
                defaults={
                    "enrollment_date": min(student.admission_date, today),
                    "status": student.status,
                },
            )
            matching = [
                s
                for s in subjects
                if s.course_id == student.course_id and s.semester == student.semester
            ]
            if new:
                enrollment.subjects.set(matching)
            for subject in matching:
                for offset in range(7):
                    Attendance.objects.get_or_create(
                        student=student,
                        subject=subject,
                        date=today - timedelta(days=offset),
                        defaults={
                            "status": rng.choices(
                                ["present", "absent", "late"], weights=[83, 10, 7]
                            )[0],
                            "class_group": classes[subject.pk],
                        },
                    )
                for exam, offset in [("midterm", 14), ("assignment", 3)]:
                    marks = [96, 87, 76, 66, 55, 43][(i + offset) % 6]
                    Result.objects.get_or_create(
                        student=student,
                        subject=subject,
                        exam_type=exam,
                        exam_date=today - timedelta(days=offset),
                        defaults={
                            "marks_obtained": marks,
                            "total_marks": 100,
                            "remarks": "Excellent progress."
                            if marks >= 80
                            else "Review the feedback and practice key concepts.",
                        },
                    )
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo ready: {Student.objects.count()} students, {Teacher.objects.count()} teachers, {Department.objects.count()} departments, {Course.objects.count()} courses, {Subject.objects.count()} subjects, {Attendance.objects.count()} attendance records, {Result.objects.count()} results."
            )
        )
        self.stdout.write(
            "Local demo login: admin / Admin@12345 (only if this command created the account). Existing credentials are preserved."
        )
