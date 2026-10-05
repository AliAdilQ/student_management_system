from django.contrib import admin

from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = [
        "teacher_id",
        "name",
        "email",
        "department",
        "specialization",
        "status",
    ]
    list_filter = ["department", "status"]
    search_fields = ["teacher_id", "name", "email"]
    date_hierarchy = "joining_date"
    list_select_related = ["department", "user"]
