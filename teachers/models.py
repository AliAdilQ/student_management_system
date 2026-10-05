from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import Status, TimestampedModel


class Teacher(TimestampedModel):
    teacher_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=25, blank=True)
    department = models.ForeignKey(
        "academics.Department", on_delete=models.PROTECT, related_name="teachers"
    )
    specialization = models.CharField(max_length=120)
    joining_date = models.DateField(default=timezone.localdate)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.ACTIVE
    )
    user = models.OneToOneField(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teacher_profile",
        help_text="Optional login account; permissions are assigned through account roles.",
    )

    class Meta:
        ordering = ["name"]

    def clean(self):
        if self.joining_date and self.joining_date > timezone.localdate():
            raise ValidationError(
                {"joining_date": "Joining date cannot be in the future."}
            )

    def __str__(self):
        return self.name
