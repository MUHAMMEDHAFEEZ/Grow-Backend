from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # ── OpenAPI schema + interactive docs ─────────────────────────────────
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # ── Legacy / existing ─────────────────────────────────────────────────
    path("accounts/", include("accounts.urls")),
    path("students/", include("students.urls")),
    # ── API v1 ────────────────────────────────────────────────────────────
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/", include("grow.api_urls")),  # courses + assignments + submissions
    path("api/v1/", include("grades.urls")),
    path("api/v1/", include("attendance.urls")),
    path("api/v1/", include("notifications.urls")),
    path("api/v1/sessions/", include("study_sessions.urls")),
    path("api/v1/xp/", include("xp.urls")),
    path("api/v1/parent/", include("parent.urls")),
    path("api/v1/ai/", include("ai.urls")),
]
