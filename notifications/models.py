from django.conf import settings
from django.db import models


class Notification(models.Model):
    class EventType(models.TextChoices):
        ASSIGNMENT_CREATED  = "assignment_created",  "Assignment Created"
        SUBMISSION_CREATED  = "submission_created",  "Submission Created"
        SUBMISSION_GRADED   = "submission_graded",   "Submission Graded"
        ATTENDANCE_MARKED   = "attendance_marked",   "Attendance Marked"
        ENROLLMENT_CREATED  = "enrollment_created",  "Enrollment Created"
        LESSON_CREATED      = "lesson_created",      "Lesson Created"
        QUIZ_CREATED        = "quiz_created",        "Quiz Created"
        QUIZ_DEADLINE       = "quiz_deadline",       "Quiz Deadline Passed"
        GRADE_UPDATED       = "grade_updated",       "Grade Updated"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    is_read = models.BooleanField(default=False)
    related_course = models.ForeignKey(
        "courses.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    related_content_id = models.PositiveIntegerField(null=True, blank=True)
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="parent_notifications",
        null=True,
        blank=True,
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_notifications",
        null=True,
        blank=True,
    )
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["related_course"]),
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["parent", "is_read"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "event_type", "reference_id"],
                name="unique_parent_notification",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.event_type}] → {self.recipient.username}: {self.title}"
