from django.urls import path
from .views import DashboardView

urlpatterns = [
    path("dashboard/<int:student_id>/", DashboardView.as_view(), name="parent-dashboard"),
]