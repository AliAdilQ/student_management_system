from django.contrib import admin

from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = [
        "student_id",
        "full_name",
        "email",
        "department",
        "course",
        "semester",
        "status",
    ]
    list_filter = ["department", "course", "semester", "gender", "status"]
    search_fields = ["student_id", "first_name", "last_name", "email"]
    date_hierarchy = "admission_date"
    readonly_fields = ["created_at", "updated_at", "attendance_rate"]
    list_select_related = ["department", "course"]
    fieldsets = [
        (
            "Identity",
            {
                "fields": [
                    "student_id",
                    ("first_name", "last_name"),
                    "gender",
                    "date_of_birth",
                    "photo",
                ]
            },
        ),
        ("Contact", {"fields": ["email", "phone", "address"]}),
        (
            "Academic record",
            {
                "fields": [
                    "department",
                    "course",
                    "semester",
                    "admission_date",
                    "status",
                    "attendance_rate",
                ]
            },
        ),
        ("History", {"fields": ["created_at", "updated_at"]}),
    ]
