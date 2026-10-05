from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.generic import RedirectView
from django.views.static import serve

from core import views

urlpatterns = [
    path(
        "favicon.ico",
        RedirectView.as_view(
            url=settings.STATIC_URL + "images/favicon.svg", permanent=False
        ),
    ),
    path("admin/", admin.site.urls),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path(
        "password/change/", views.PasswordChangeView.as_view(), name="password-change"
    ),
    path("attendance/register/", views.attendance_register, name="attendance-register"),
    path("<slug:module>/", views.RecordListView.as_view(), name="record-list"),
    path("<slug:module>/add/", views.RecordCreateView.as_view(), name="record-add"),
    path(
        "<slug:module>/<int:pk>/",
        views.RecordDetailView.as_view(),
        name="record-detail",
    ),
    path(
        "<slug:module>/<int:pk>/edit/",
        views.RecordUpdateView.as_view(),
        name="record-edit",
    ),
    path(
        "<slug:module>/<int:pk>/delete/",
        views.RecordDeleteView.as_view(),
        name="record-delete",
    ),
]
if settings.DEBUG:
    urlpatterns.insert(
        0,
        path(
            "media/<path:path>",
            login_required(serve),
            {"document_root": settings.MEDIA_ROOT},
        ),
    )
