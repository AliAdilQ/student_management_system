from django.contrib import admin

from .models import Result


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "subject",
        "exam_type",
        "exam_date",
        "marks_obtained",
        "total_marks",
        "percentage",
        "grade",
    ]
    list_filter = ["subject", "exam_type", "exam_date"]
    search_fields = [
        "student__student_id",
        "student__first_name",
        "student__last_name",
        "subject__name",
    ]
    date_hierarchy = "exam_date"
    readonly_fields = ["percentage", "grade", "created_at", "updated_at"]
    list_select_related = ["student", "subject"]
