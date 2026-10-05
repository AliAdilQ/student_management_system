from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from core.models import TimestampedModel


class Result(TimestampedModel):
    class ExamType(models.TextChoices):
        QUIZ = "quiz", "Quiz"
        ASSIGNMENT = "assignment", "Assignment"
        MIDTERM = "midterm", "Midterm"
        FINAL = "final", "Final"

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="results"
    )
    subject = models.ForeignKey(
        "academics.Subject", on_delete=models.PROTECT, related_name="results"
    )
    exam_type = models.CharField(max_length=12, choices=ExamType.choices)
    exam_date = models.DateField()
    marks_obtained = models.DecimalField(
        max_digits=6, decimal_places=2, validators=[MinValueValidator(0)]
    )
    total_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=100,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-exam_date", "student__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "subject", "exam_type", "exam_date"],
                name="unique_exam_result",
            ),
            models.CheckConstraint(
                condition=models.Q(total_marks__gt=0)
                & models.Q(marks_obtained__gte=0)
                & models.Q(marks_obtained__lte=models.F("total_marks")),
                name="valid_result_marks",
            ),
        ]

    @property
    def raw_percentage(self):
        return (
            Decimal(str(self.marks_obtained)) * 100 / Decimal(str(self.total_marks))
            if self.total_marks
            else Decimal(0)
        )

    @property
    def percentage(self):
        return self.raw_percentage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def grade(self):
        for threshold, grade in [
            (90, "A+"),
            (80, "A"),
            (70, "B"),
            (60, "C"),
            (50, "D"),
        ]:
            if self.raw_percentage >= threshold:
                return grade
        return "F"

    def clean(self):
        errors = {}
        if (
            self.marks_obtained is not None
            and self.total_marks is not None
            and self.marks_obtained > self.total_marks
        ):
            errors["marks_obtained"] = "Marks obtained cannot exceed total marks."
        if (
            self.student_id
            and self.subject_id
            and self.student.course_id != self.subject.course_id
        ):
            errors["subject"] = "The subject must belong to the student's course."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.student} · {self.subject.code} · {self.get_exam_type_display()}"
