"""
dashboard/urls.py — URL routing for dashboard API endpoints.
"""

from django.urls import path

from . import views

urlpatterns = [
    path("overview/", views.dashboard_overview, name="dashboard-overview"),
    path("classes/", views.classes_list, name="classes-list"),
    path("classes/<int:class_id>/", views.class_detail, name="class-detail"),
    path("students/<int:student_id>/", views.student_profile, name="student-profile"),
    path(
        "students/<int:student_id>/notes/",
        views.student_note_create,
        name="student-note-create",
    ),
    path("reports/", views.report_view, name="report-view"),
    path("reports/export/", views.report_export, name="report-export"),
    path("risk-summary/", views.risk_summary, name="risk-summary"),
    path(
        "insights/<int:insight_id>/dismiss/",
        views.insight_dismiss,
        name="insight-dismiss",
    ),
]
