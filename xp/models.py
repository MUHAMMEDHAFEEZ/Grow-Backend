from django.conf import settings
from django.db import models


class XPTransaction(models.Model):
    class SourceType(models.TextChoices):
        LESSON = "lesson", "Lesson"
        QUIZ = "quiz", "Quiz"
        ASSIGNMENT = "assignment", "Assignment"
        TASK = "task", "Task"
        STREAK = "streak", "Streak"

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
    xp_amount = models.IntegerField()
    source = models.CharField(max_length=20, choices=Source.choices)
    source_type = models.CharField(max_length=20, choices=SourceType.choices, null=True, blank=True)
    source_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "source_type", "source_id"],
                name="unique_xp_source",
            ),
        ]
        indexes = [
            models.Index(fields=["student", "created_at"]),
        ]

    def __str__(self):
        return f"XPTransaction(student={self.student_id}, xp={self.xp_amount}, source={self.source})"
