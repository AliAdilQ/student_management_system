from datetime import timedelta
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, DateField, Q
from django.db.models.deletion import ProtectedError
from django.forms import modelform_factory
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from academics.models import ClassGroup, Course, Department, Enrollment, Subject
from attendance.models import Attendance
from results.models import Result
from students.models import Student
from teachers.models import Teacher

from .forms import (
    AccountCreateForm,
    AccountUpdateForm,
    LoginForm,
    RecordForm,
    StyledFormMixin,
)
from .registry import MODULES


class LoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


@login_required
def dashboard(request):
    today = timezone.localdate()
    counts = {
        "students": Student.objects.count(),
        "teachers": Teacher.objects.count(),
        "courses": Course.objects.count(),
        "departments": Department.objects.count(),
        "subjects": Subject.objects.count(),
        "enrollments": Enrollment.objects.count(),
    }
    attendance = Attendance.objects.all()
    total = attendance.count()
    rate = (
        round(attendance.exclude(status="absent").count() / total * 100, 1)
        if total
        else 0
    )
    today_records = attendance.filter(date=today)
    today_total = today_records.count()
    today_attended = today_records.exclude(status="absent").count()
    departments = list(
        Department.objects.annotate(total=Count("students")).values("code", "total")
    )
    status_counts = {
        item["status"]: item["total"]
        for item in attendance.values("status").annotate(total=Count("id"))
    }
    grades = {grade: 0 for grade in ["A+", "A", "B", "C", "D", "F"]}
    for result in Result.objects.only("marks_obtained", "total_marks"):
        grades[result.grade] += 1
    course_counts = list(
        Course.objects.annotate(total=Count("enrollments")).values("code", "total")
    )
    trend = []
    for days in range(6, -1, -1):
        day = today - timedelta(days=days)
        records = attendance.filter(date=day)
        count = records.count()
        trend.append(
            {
                "label": day.strftime("%a"),
                "rate": round(records.exclude(status="absent").count() / count * 100, 1)
                if count
                else None,
            }
        )
    return render(
        request,
        "core/dashboard.html",
        {
            "counts": counts,
            "today": today,
            "rate": rate,
            "today_total": today_total,
            "today_attended": today_attended,
            "recent_students": Student.objects.select_related(
                "department", "course"
            ).order_by("-created_at")[:5],
            "recent_results": Result.objects.select_related(
                "student", "subject"
            ).order_by("-created_at")[:4],
            "chart_data": {
                "departments": departments,
                "attendance": status_counts,
                "grades": grades,
                "courses": course_counts,
                "trend": trend,
            },
            "active_students": Student.objects.filter(status="active").count(),
        },
    )


def display_value(obj, name):
    value = getattr(obj, name, None)
    method = getattr(obj, f"get_{name}_display", None)
    if method:
        value = method()
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if hasattr(value, "strftime"):
        return value.strftime("%b %d, %Y")
    return value if value is not None and value != "" else "—"


class ModuleMixin(LoginRequiredMixin):
    action = "view"

    def dispatch(self, request, *args, **kwargs):
        self.module = kwargs["module"]
        if self.module not in MODULES:
            raise Http404
        self.config = MODULES[self.module]
        self.model = self.config["model"]
        if request.user.is_authenticated:
            if self.module == "accounts" and not request.user.is_superuser:
                raise PermissionDenied
            if self.action != "view" and not self.allowed(self.action):
                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def allowed(self, action):
        if self.module == "accounts":
            return self.request.user.is_superuser
        return self.request.user.has_perm(
            f"{self.model._meta.app_label}.{action}_{self.model._meta.model_name}"
        )

    def get_queryset(self):
        return self.model.objects.select_related(*self.config["select"]).all()

    def get_success_url(self):
        return reverse("record-list", kwargs={"module": self.module})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            config=self.config,
            module=self.module,
            can_add=self.allowed("add"),
            can_edit=self.allowed("change"),
            can_delete=self.allowed("delete"),
        )
        return context


class RecordListView(ModuleMixin, ListView):
    template_name = "core/record_list.html"
    paginate_by = 10

    def filter_form(self):
        fields = {
            "q": forms.CharField(
                required=False,
                label="Search",
                widget=forms.TextInput(
                    attrs={
                        "class": "form-control",
                        "placeholder": f"Search {self.config['title'].lower()}…",
                    }
                ),
            )
        }
        for name in self.config["filters"]:
            field = self.model._meta.get_field(name)
            if field.is_relation:
                fields[name] = forms.ModelChoiceField(
                    queryset=field.related_model.objects.all(),
                    required=False,
                    empty_label=f"All {field.verbose_name}s",
                )
            elif field.choices:
                fields[name] = forms.ChoiceField(
                    choices=[("", f"All {field.verbose_name}s"), *field.choices],
                    required=False,
                )
            elif isinstance(field, DateField):
                fields[name] = forms.DateField(
                    required=False, widget=forms.DateInput(attrs={"type": "date"})
                )
            elif name == "is_active":
                fields[name] = forms.ChoiceField(
                    choices=[("", "All accounts"), ("1", "Active"), ("0", "Inactive")],
                    required=False,
                )
            else:
                fields[name] = forms.ChoiceField(
                    choices=[
                        ("", "All semesters"),
                        *[(n, f"Semester {n}") for n in range(1, 13)],
                    ],
                    required=False,
                )
        cls = type("Filters", (StyledFormMixin, forms.Form), fields)
        return cls(self.request.GET)

    def get_queryset(self):
        queryset = super().get_queryset()
        self.filters = self.filter_form()
        if self.filters.is_valid():
            data = self.filters.cleaned_data
            query = data.get("q", "").strip()
            if query:
                condition = Q()
                for name in self.config["search"]:
                    condition |= Q(**{f"{name}__icontains": query})
                queryset = queryset.filter(condition)
            for name in self.config["filters"]:
                value = data.get(name)
                if value not in (None, ""):
                    queryset = queryset.filter(
                        **{name: value == "1" if name == "is_active" else value}
                    )
        sort = self.request.GET.get("sort", "")
        allowed = {
            name
            for name, _ in self.config["columns"]
            if name not in {"full_name", "percentage", "grade"}
        }
        if sort.lstrip("-") in allowed:
            queryset = queryset.order_by(sort, "pk")
        elif self.module == "accounts":
            queryset = queryset.order_by("username")
        else:
            queryset = queryset.order_by(*self.model._meta.ordering, "pk")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filters"] = self.filters
        context["rows"] = [
            {
                "object": obj,
                "cells": [
                    {"value": display_value(obj, name), "key": name}
                    for name, _ in self.config["columns"]
                ],
            }
            for obj in context["object_list"]
        ]
        params = self.request.GET.copy()
        params.pop("page", None)
        context["query_params"] = params.urlencode()
        context["sort_options"] = [
            (name, label)
            for name, label in self.config["columns"]
            if name not in {"full_name", "percentage", "grade"}
        ]
        if self.module == "attendance":
            queryset = self.object_list
            context["summary"] = [
                ("Present", queryset.filter(status="present").count(), "green"),
                ("Absent", queryset.filter(status="absent").count(), "red"),
                ("Late", queryset.filter(status="late").count(), "amber"),
            ]
        if self.module == "results":
            records = list(self.object_list)
            average = (
                sum((r.percentage for r in records), Decimal(0)) / len(records)
                if records
                else 0
            )
            context["summary"] = [
                ("Assessments", len(records), "blue"),
                ("Average score", f"{average:.1f}%", "green"),
                ("Passing results", sum(r.grade != "F" for r in records), "purple"),
            ]
        return context


class RecordDetailView(ModuleMixin, DetailView):
    template_name = "core/record_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        excluded = {"id", "password", "photo"}
        if self.module == "accounts":
            names = [
                "username",
                "first_name",
                "last_name",
                "email",
                "is_active",
                "is_staff",
                "is_superuser",
                "last_login",
                "date_joined",
            ]
        else:
            names = [f.name for f in self.model._meta.fields if f.name not in excluded]
        context["details"] = [
            (
                self.model._meta.get_field(name).verbose_name,
                display_value(self.object, name),
            )
            for name in names
        ]
        if self.module == "students":
            context.update(
                attendance_rate=self.object.attendance_rate,
                related_results=self.object.results.select_related("subject")[:6],
                related_enrollments=self.object.enrollments.select_related("course")[
                    :6
                ],
                related_attendance=self.object.attendance_records.select_related(
                    "subject"
                )[:6],
            )
        if self.module == "results":
            context["details"] += [
                ("Percentage", f"{self.object.percentage}%"),
                ("Grade", self.object.grade),
            ]
        if self.module == "enrollments":
            context["details"] += [
                (
                    "Subjects",
                    ", ".join(str(s) for s in self.object.subjects.all())
                    or "All course subjects",
                )
            ]
        if self.module == "accounts":
            context["details"] += [
                (
                    "Roles",
                    ", ".join(self.object.groups.values_list("name", flat=True))
                    or "Custom / superuser",
                )
            ]
        return context


class RecordFormMixin(ModuleMixin):
    template_name = "core/record_form.html"

    def get_form_class(self):
        if self.module == "accounts":
            return AccountCreateForm if self.action == "add" else AccountUpdateForm
        return modelform_factory(
            self.model, form=RecordForm, exclude=["created_at", "updated_at"]
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"{self.config['singular'].capitalize()} {'created' if self.action == 'add' else 'updated'} successfully.",
        )
        return response

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "editing": self.action == "change",
        }


class RecordCreateView(RecordFormMixin, CreateView):
    action = "add"


class RecordUpdateView(RecordFormMixin, UpdateView):
    action = "change"


class RecordDeleteView(ModuleMixin, DeleteView):
    action = "delete"
    template_name = "core/record_confirm_delete.html"

    def form_valid(self, form):
        if self.module == "accounts" and (
            self.object == self.request.user
            or self.object.is_superuser
            and not User.objects.filter(is_superuser=True, is_active=True)
            .exclude(pk=self.object.pk)
            .exists()
        ):
            messages.error(
                self.request,
                "You cannot delete your own account or the last active superuser.",
            )
            return redirect("record-detail", module=self.module, pk=self.object.pk)
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "This record has linked academic data. Remove or reassign those records first.",
            )
            return redirect("record-detail", module=self.module, pk=self.object.pk)
        messages.success(
            self.request,
            f"{self.config['singular'].capitalize()} deleted successfully.",
        )
        return response


class AttendanceRegisterForm(StyledFormMixin, forms.Form):
    subject = forms.ModelChoiceField(queryset=Subject.objects.select_related("course"))
    class_group = forms.ModelChoiceField(
        queryset=ClassGroup.objects.all(), required=False, label="Class (optional)"
    )
    date = forms.DateField(initial=timezone.localdate)

    def clean(self):
        data = super().clean()
        if data.get("date") and data["date"] > timezone.localdate():
            self.add_error("date", "Choose today or an earlier date.")
        if (
            data.get("subject")
            and data.get("class_group")
            and data["class_group"].subject_id != data["subject"].pk
        ):
            self.add_error("class_group", "Select a class for this subject.")
        return data


@login_required
@permission_required("attendance.add_attendance", raise_exception=True)
def attendance_register(request):
    form = AttendanceRegisterForm(
        request.POST if request.method == "POST" else request.GET or None
    )
    roster = []
    if form.is_bound and form.is_valid():
        data = form.cleaned_data
        students = Student.objects.filter(
            course=data["subject"].course, status="active"
        ).order_by("first_name", "last_name")
        existing = {
            r.student_id: r.status
            for r in Attendance.objects.filter(
                subject=data["subject"], date=data["date"]
            )
        }
        roster = [
            {
                "student": student,
                "status": request.POST.get(
                    f"status_{student.pk}", existing.get(student.pk, "present")
                ),
            }
            for student in students
        ]
        if request.method == "POST":
            if existing and not request.user.has_perm("attendance.change_attendance"):
                raise PermissionDenied
            if not roster:
                form.add_error(
                    None, "No active students are registered for this course."
                )
            elif any(row["status"] not in Attendance.Status.values for row in roster):
                form.add_error(
                    None, "Select Present, Absent, or Late for every student."
                )
            else:
                with transaction.atomic():
                    for row in roster:
                        Attendance.objects.update_or_create(
                            student=row["student"],
                            subject=data["subject"],
                            date=data["date"],
                            defaults={
                                "status": row["status"],
                                "class_group": data["class_group"],
                            },
                        )
                messages.success(
                    request, f"Attendance saved for {len(roster)} students."
                )
                return redirect(
                    reverse("record-list", kwargs={"module": "attendance"})
                    + f"?subject={data['subject'].pk}&date={data['date']}"
                )
    return render(
        request,
        "attendance/register.html",
        {"form": form, "roster": roster, "active_module": "attendance"},
    )


@login_required
def profile(request):
    return render(request, "core/profile.html")


def csrf_failure(request, reason=""):
    return render(
        request,
        "403.html",
        {
            "error_heading": "Your form session needs a refresh.",
            "error_description": "Refresh the page and submit the form again. Your request could not be verified, so no changes were saved.",
        },
        status=403,
    )


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    pass


class PasswordChangeView(LoginRequiredMixin, auth_views.PasswordChangeView):
    template_name = "registration/password_change.html"
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy("profile")

    def form_valid(self, form):
        messages.success(self.request, "Your password was changed successfully.")
        return super().form_valid(form)
