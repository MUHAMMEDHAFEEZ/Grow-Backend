from django.conf import settings
from django.db import models


class StudentTask(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_tasks",
    )
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, related_name="student_tasks"
    )
    content_type = models.CharField(max_length=50)
    content_id = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "content_type", "content_id"],
                name="uq_student_content",
            )
        ]
        indexes = [
            models.Index(fields=["student", "status"]),
            models.Index(fields=["course", "status"]),
            models.Index(fields=["content_type", "content_id"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.status}] {self.title} — {self.student.username}"
