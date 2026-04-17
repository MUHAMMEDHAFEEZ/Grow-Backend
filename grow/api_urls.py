"""
grow/api_urls.py — Central API router registration for /api/v1/

Uses DefaultRouter for the root (adds browsable API) and SimpleRouter-based
nested routers to avoid duplicate drf_format_suffix converter registration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers as nested_routers

from courses.views import (
    AssignmentViewSet,
    CourseViewSet,
    LessonViewSet,
    SubmissionViewSet,
)

# Root router — DefaultRouter gives the browsable API root
root_router = DefaultRouter()
root_router.register(r"courses", CourseViewSet, basename="course")
root_router.register(r"lessons", LessonViewSet, basename="lesson")

# Nested routers use SimpleRouter to avoid duplicate converter registration
assignments_router = nested_routers.NestedSimpleRouter(
    root_router, r"courses", lookup="course"
)
assignments_router.register(
    r"assignments", AssignmentViewSet, basename="course-assignment"
)

submissions_router = nested_routers.NestedSimpleRouter(
    assignments_router, r"assignments", lookup="assignment"
)
submissions_router.register(
    r"submissions", SubmissionViewSet, basename="assignment-submission"
)

urlpatterns = [
    path("", include(root_router.urls)),
    path("", include(assignments_router.urls)),
    path("", include(submissions_router.urls)),
]
