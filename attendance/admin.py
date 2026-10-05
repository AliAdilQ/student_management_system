from django.contrib import admin

from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ["student", "subject", "class_group", "date", "status"]
    list_filter = ["date", "status", "subject", "class_group"]
    search_fields = [
        "student__student_id",
        "student__first_name",
        "student__last_name",
        "subject__name",
    ]
    date_hierarchy = "date"
    list_select_related = ["student", "subject", "class_group"]
