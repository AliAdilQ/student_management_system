from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import Status, TimestampedModel


def validate_photo(photo):
    if photo.size > 2 * 1024 * 1024:
        raise ValidationError("Profile photos must be smaller than 2 MB.")


class Student(TimestampedModel):
    class Gender(models.TextChoices):
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        OTHER = "other", "Other / prefer not to say"

    student_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=25, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    date_of_birth = models.DateField()
    address = models.TextField(blank=True)
    department = models.ForeignKey(
        "academics.Department", on_delete=models.PROTECT, related_name="students"
    )
    course = models.ForeignKey(
        "academics.Course", on_delete=models.PROTECT, related_name="students"
    )
    semester = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    admission_date = models.DateField(default=timezone.localdate)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.ACTIVE
    )
    photo = models.ImageField(
        upload_to="students/%Y/%m/", blank=True, validators=[validate_photo]
    )

    class Meta:
        ordering = ["first_name", "last_name"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def initials(self):
        return (self.first_name[:1] + self.last_name[:1]).upper()

    @property
    def year(self):
        return (self.semester + 1) // 2

    @property
    def attendance_rate(self):
        records = self.attendance_records.all()
        total = records.count()
        return (
            round(records.exclude(status="absent").count() / total * 100, 1)
            if total
            else 0
        )

    def clean(self):
        errors = {}
        today = timezone.localdate()
        if (
            self.course_id
            and self.department_id
            and self.course.department_id != self.department_id
        ):
            errors["course"] = "The selected course must belong to the department."
        if (
            self.course_id
            and self.semester
            and self.semester > self.course.duration * 2
        ):
            errors["semester"] = "Semester exceeds this course's duration."
        if self.date_of_birth and self.date_of_birth >= today:
            errors["date_of_birth"] = "Date of birth must be in the past."
        if self.admission_date and self.admission_date > today:
            errors["admission_date"] = "Admission date cannot be in the future."
        if (
            self.date_of_birth
            and self.admission_date
            and self.admission_date <= self.date_of_birth
        ):
            errors["admission_date"] = "Admission date must be after date of birth."
        if self.pk and self.course_id:
            previous = type(self).objects.get(pk=self.pk)
            if previous.course_id != self.course_id and (
                self.enrollments.exists()
                or self.attendance_records.exists()
                or self.results.exists()
            ):
                errors["course"] = (
                    "Remove linked academic records before changing this student's course."
                )
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.full_name
