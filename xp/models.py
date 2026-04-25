from django.conf import settings
from django.db import models


class XPTransaction(models.Model):
    """
    Tracks XP earned by students from various activities.
    """

    class Source(models.TextChoices):
        STUDY = "study", "Study Session"
        ASSIGNMENT = "assignment", "Assignment"
        QUIZ = "quiz", "Quiz"
        ATTENDANCE = "attendance", "Attendance"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="xp_transactions",
    )
    xp = models.IntegerField()
    source = models.CharField(max_length=20, choices=Source.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "created_at"]),
        ]

    def __str__(self):
        return f"XPTransaction(student={self.student_id}, xp={self.xp}, source={self.source})"
