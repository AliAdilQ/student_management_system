from django.contrib import admin
from django.forms import modelform_factory

from core.forms import RecordForm

from .models import ClassGroup, Course, Department, Enrollment, Subject


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "updated_at"]
    search_fields = ["name", "code"]
    ordering = ["name"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "department", "duration"]
    list_filter = ["department", "duration"]
    search_fields = ["name", "code"]
    list_select_related = ["department"]


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "course", "teacher", "semester", "credit_hours"]
    list_filter = ["course", "semester", "teacher"]
    search_fields = ["name", "code"]
    list_select_related = ["course", "teacher"]


@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "subject", "room", "schedule", "capacity"]
    list_filter = ["subject"]
    search_fields = ["name", "room", "subject__name"]
    list_select_related = ["subject"]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    form = modelform_factory(Enrollment, form=RecordForm, exclude=[])
    list_display = [
        "student",
        "course",
        "semester",
        "academic_year",
        "status",
        "enrollment_date",
    ]
    list_filter = ["course", "semester", "academic_year", "status"]
    search_fields = ["student__student_id", "student__first_name", "student__last_name"]
    date_hierarchy = "enrollment_date"
    filter_horizontal = ["subjects"]
    list_select_related = ["student", "course"]
