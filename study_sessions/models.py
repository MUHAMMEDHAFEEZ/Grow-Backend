from django.conf import settings
from django.db import models


class StudySession(models.Model):
    """
    Persistent study session model.
    Tracks start/end times for student study sessions.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_sessions",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)
    xp_earned = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["student", "ended_at"]),
            models.Index(fields=["student", "started_at"]),
        ]

    def __str__(self):
        return f"StudySession(student={self.student_id}, started={self.started_at})"

    @property
    def is_active(self):
        return self.ended_at is None
