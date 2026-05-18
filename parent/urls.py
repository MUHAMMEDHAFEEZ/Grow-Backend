from django.urls import path
from .views import (
    DashboardView,
    SettingsView,
    add_student,
    analytics,
    attendance,
    list_students,
    notification_read,
    notifications_list,
    report,
    report_print,
)

urlpatterns = [
    path("add-student/", add_student, name="parent-add-student"),
    path("students/", list_students, name="parent-list-students"),
    path("dashboard/<str:student_code>/", DashboardView.as_view(), name="parent-dashboard"),
    path("analytics/<str:student_code>/", analytics, name="parent-analytics"),
    path("attendance/<str:student_code>/", attendance, name="parent-attendance"),
    path("report/<str:student_code>/", report, name="parent-report"),
    path("report/<str:student_code>/print/", report_print, name="parent-report-print"),
    path("notifications/", notifications_list, name="parent-notifications"),
    path("notifications/<int:notification_id>/read/", notification_read, name="parent-notification-read"),
    path("settings/", SettingsView.as_view(), name="parent-settings"),
]
