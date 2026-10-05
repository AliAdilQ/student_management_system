from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

from core.models import Status, TimestampedModel


class Department(TimestampedModel):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=12, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Course(TimestampedModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="courses"
    )
    duration = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        help_text="Duration in years (1–6).",
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def clean(self):
        if self.pk:
            old = type(self).objects.get(pk=self.pk)
            if self.department_id != old.department_id and self.students.exists():
                raise ValidationError(
                    {
                        "department": "Reassign linked students before changing the course's department."
                    }
                )
            if self.duration and (
                self.students.filter(semester__gt=self.duration * 2).exists()
                or self.subjects.filter(semester__gt=self.duration * 2).exists()
                or self.enrollments.filter(semester__gt=self.duration * 2).exists()
            ):
                raise ValidationError(
                    {
                        "duration": "The duration is too short for existing student, subject, or enrollment semesters."
                    }
                )

    def __str__(self):
        return self.name


class Subject(TimestampedModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, unique=True)
    course = models.ForeignKey(
        Course, on_delete=models.PROTECT, related_name="subjects"
    )
    teacher = models.ForeignKey(
        "teachers.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subjects",
    )
    credit_hours = models.PositiveSmallIntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(6)]
    )
    semester = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(12)]
    )

    class Meta:
        ordering = ["course__name", "semester", "name"]

    def clean(self):
        if (
            self.course_id
            and self.semester
            and self.semester > self.course.duration * 2
        ):
            raise ValidationError(
                {"semester": "Semester exceeds this course's duration."}
            )
        if self.pk and self.course_id:
            old = type(self).objects.get(pk=self.pk)
            linked = (
                self.attendance_records.exists()
                or self.results.exists()
                or self.enrollments.exists()
            )
            if (
                old.course_id != self.course_id or old.semester != self.semester
            ) and linked:
                raise ValidationError(
                    "Remove linked enrollments, attendance, and results before changing the subject's course or semester."
                )

    def __str__(self):
        return f"{self.code} · {self.name}"


class ClassGroup(TimestampedModel):
    name = models.CharField(max_length=80)
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="classes"
    )
    room = models.CharField(max_length=40)
    schedule = models.CharField(
        max_length=120, help_text="For example: Monday & Wednesday, 09:00–10:30"
    )
    capacity = models.PositiveSmallIntegerField(
        default=30, validators=[MinValueValidator(1), MaxValueValidator(500)]
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "subject"], name="unique_subject_class"
            )
        ]
        verbose_name = "class"
        verbose_name_plural = "classes"

    def __str__(self):
        return f"{self.name} · {self.subject.code}"

    def clean(self):
        if self.pk and self.subject_id:
            old = type(self).objects.get(pk=self.pk)
            if old.subject_id != self.subject_id and self.attendance_records.exists():
                raise ValidationError(
                    {
                        "subject": "Reassign linked attendance before changing the class's subject."
                    }
                )


class Enrollment(TimestampedModel):
    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="enrollments"
    )
    course = models.ForeignKey(
        Course, on_delete=models.PROTECT, related_name="enrollments"
    )
    subjects = models.ManyToManyField(
        Subject,
        blank=True,
        related_name="enrollments",
        help_text="Optional subject selection within the course and semester.",
    )
    semester = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    academic_year = models.CharField(
        max_length=9,
        validators=[RegexValidator(r"^\d{4}-\d{4}$", "Use the format 2026-2027.")],
    )
    enrollment_date = models.DateField(default=timezone.localdate)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.ACTIVE
    )

    class Meta:
        ordering = ["-enrollment_date", "student__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course", "semester", "academic_year"],
                name="unique_student_course_term",
            )
        ]

    def clean(self):
        errors = {}
        if (
            self.course_id
            and self.student_id
            and self.student.course_id != self.course_id
        ):
            errors["course"] = "Select the student's current course."
        if (
            self.course_id
            and self.semester
            and self.semester > self.course.duration * 2
        ):
            errors["semester"] = "Semester exceeds this course's duration."
        if (
            self.academic_year
            and len(self.academic_year) == 9
            and self.academic_year[:4].isdigit()
            and self.academic_year[5:].isdigit()
        ):
            if int(self.academic_year[5:]) != int(self.academic_year[:4]) + 1:
                errors["academic_year"] = "Academic years must be consecutive."
        if self.enrollment_date and self.enrollment_date > timezone.localdate():
            errors["enrollment_date"] = "Enrollment date cannot be in the future."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.student} · {self.academic_year} / S{self.semester}"
