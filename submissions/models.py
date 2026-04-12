from django.conf import settings
from django.db import models

from assignments.models import Assignment


class Submission(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        GRADED  = "graded",  "Graded"

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
        limit_choices_to={"role": "student"},
    )
    content = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("assignment", "student")
        ordering = ["-submitted_at"]

    def __str__(self) -> str:
        return f"{self.student.username} → {self.assignment.title}"
