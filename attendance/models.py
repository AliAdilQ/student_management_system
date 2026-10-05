from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import TimestampedModel


class Attendance(TimestampedModel):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="attendance_records"
    )
    subject = models.ForeignKey(
        "academics.Subject", on_delete=models.PROTECT, related_name="attendance_records"
    )
    class_group = models.ForeignKey(
        "academics.ClassGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
    )
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PRESENT
    )
    remarks = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-date", "student__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "subject", "date"],
                name="unique_daily_subject_attendance",
            )
        ]
        verbose_name_plural = "attendance records"

    def clean(self):
        errors = {}
        if (
            self.student_id
            and self.subject_id
            and self.student.course_id != self.subject.course_id
        ):
            errors["subject"] = "The subject must belong to the student's course."
        if (
            self.class_group_id
            and self.subject_id
            and self.class_group.subject_id != self.subject_id
        ):
            errors["class_group"] = "The class must belong to the selected subject."
        if self.date and self.date > timezone.localdate():
            errors["date"] = "Attendance cannot be recorded for a future date."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.student} · {self.subject.code} · {self.date}"
