"""
core/models.py — Shared models used across the platform.
"""

from django.conf import settings
from django.db import models


class ActivityLog(models.Model):
    class EventType(models.TextChoices):
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"
        COURSE_OPENED = "course_opened", "Course opened"
        LESSON_COMPLETED = "lesson_completed", "Lesson completed"
        QUIZ_SUBMITTED = "quiz_submitted", "Quiz submitted"
        ASSIGNMENT_SUBMITTED = "assignment_submitted", "Assignment submitted"
        ATTENDANCE_MARKED = "attendance_marked", "Attendance marked"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activity_logs",
    )
    event_type = models.CharField(max_length=50, choices=EventType.choices)
    target_id = models.PositiveIntegerField(null=True, blank=True)
    target_type = models.CharField(max_length=50, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
        ]
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"

    def __str__(self) -> str:
        return f"{self.actor} | {self.event_type} @ {self.created_at.isoformat()}"

