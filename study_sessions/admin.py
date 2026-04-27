from django.contrib import admin
from study_sessions.models import StudySession


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ["id", "student", "started_at", "ended_at", "duration", "xp_earned"]
    list_filter = ["started_at"]
    search_fields = ["student__username", "student__email"]
    raw_id_fields = ["student"]
