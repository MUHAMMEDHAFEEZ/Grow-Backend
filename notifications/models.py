from django.conf import settings
from django.db import models


class Notification(models.Model):
    class EventType(models.TextChoices):
        ASSIGNMENT_CREATED  = "assignment_created",  "Assignment Created"
        SUBMISSION_CREATED  = "submission_created",  "Submission Created"
        SUBMISSION_GRADED   = "submission_graded",   "Submission Graded"
        ATTENDANCE_MARKED   = "attendance_marked",   "Attendance Marked"
        ENROLLMENT_CREATED  = "enrollment_created",  "Enrollment Created"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self) -> str:
        return f"[{self.event_type}] → {self.recipient.username}: {self.title}"
