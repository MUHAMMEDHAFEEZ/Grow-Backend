from django.conf import settings
from django.db import models

from submissions.models import Submission


class Grade(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name="grade")
    score = models.DecimalField(max_digits=5, decimal_places=2)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="given_grades",
    )
    graded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-graded_at"]

    def __str__(self) -> str:
        return f"Grade {self.score} for {self.submission}"
