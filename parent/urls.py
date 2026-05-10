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
    path("dashboard/<int:student_id>/", DashboardView.as_view(), name="parent-dashboard"),
    path("analytics/<int:student_id>/", analytics, name="parent-analytics"),
    path("attendance/<int:student_id>/", attendance, name="parent-attendance"),
    path("report/<int:student_id>/", report, name="parent-report"),
    path("report/<int:student_id>/print/", report_print, name="parent-report-print"),
    path("notifications/", notifications_list, name="parent-notifications"),
    path("notifications/<int:notification_id>/read/", notification_read, name="parent-notification-read"),
    path("settings/", SettingsView.as_view(), name="parent-settings"),
]