import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def _default_token_expiry():
    return timezone.now() + timedelta(hours=24)


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        PARENT = "parent", "Parent"
        TEACHER = "teacher", "Teacher"
        SCHOOL_ADMIN = "school_admin", "School Admin"

    role = models.CharField(max_length=12, choices=Role.choices)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, default="")
    avatar = models.URLField(blank=True, default="")
    # Nullable — set for teachers and students to link them to a school
    school = models.ForeignKey(
        "School",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"

    @property
    def is_teacher(self) -> bool:
        return self.role == self.Role.TEACHER

    @property
    def is_student(self) -> bool:
        return self.role == self.Role.STUDENT

    @property
    def is_parent(self) -> bool:
        return self.role == self.Role.PARENT

    @property
    def is_school_admin(self) -> bool:
        return self.role == self.Role.SCHOOL_ADMIN


class School(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    created_by = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="owned_school",
        limit_choices_to={"role": "school_admin"},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            self.slug = base
            n = 1
            while School.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base}-{n}"
                n += 1
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class ParentProfile(models.Model):
    """Links a parent user to their child (student)."""

    parent = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="parent_profile",
        limit_choices_to={"role": "parent"},
    )
    child = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="parent_links",
        limit_choices_to={"role": "student"},
    )

    class Meta:
        unique_together = ("parent", "child")

    def __str__(self) -> str:
        return f"{self.parent.username} -> {self.child.username}"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reset_tokens"
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=_default_token_expiry)
    is_used = models.BooleanField(default=False)

    @property
    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self) -> str:
        return f"ResetToken({self.user.email}, used={self.is_used})"
