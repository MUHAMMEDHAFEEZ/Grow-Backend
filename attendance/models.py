from django.conf import settings
from django.db import models

from courses.models import Course


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT  = "absent",  "Absent"
        LATE    = "late",    "Late"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="attendance_records")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendance_records",
        limit_choices_to={"role": "student"},
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="marked_attendance",
    )

    class Meta:
        unique_together = ("course", "student", "date")
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["course", "date"]),
            models.Index(fields=["student", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.student.username} | {self.course.title} | {self.date} | {self.status}"
