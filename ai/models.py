from django.conf import settings
from django.db import models


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
        limit_choices_to={"role": "student"},
    )
    role = models.CharField(max_length=9, choices=Role.choices)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["student", "created_at"]),
        ]

    def __str__(self):
        return f"ChatMessage(student={self.student_id}, role={self.role})"
