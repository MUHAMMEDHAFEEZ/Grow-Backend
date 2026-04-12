import uuid
from datetime import timedelta

from django.conf import settings
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


# ── Enrollment Code System ────────────────────────────────────────────────────


class EnrollmentCode(models.Model):
    """Single-use cryptographically random token tied to a school."""

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        USED      = "used",      "Used"
        REVOKED   = "revoked",   "Revoked"

    school     = models.ForeignKey(
        "School", on_delete=models.CASCADE, related_name="enrollment_codes"
    )
    token      = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status     = models.CharField(
        max_length=10, choices=Status.choices, default=Status.AVAILABLE
    )
    used_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="used_codes",
    )
    used_at    = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="revoked_codes",
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["school", "status"]),
        ]

    def __str__(self) -> str:
        return f"EnrollmentCode({self.token}, {self.status}, school={self.school_id})"


class SchoolMembership(models.Model):
    """Junction table: a user's membership in a school with a role."""

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"
        ADMIN   = "admin",   "Admin"

    user      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="school_memberships"
    )
    school    = models.ForeignKey(
        "School", on_delete=models.CASCADE, related_name="memberships"
    )
    role      = models.CharField(max_length=10, choices=Role.choices)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "school")
        indexes = [
            models.Index(fields=["user", "role"]),
        ]

    def __str__(self) -> str:
        return f"SchoolMembership({self.user_id}, {self.school_id}, {self.role})"


class EnrollmentRateLimit(models.Model):
    """Per-user DB counter for rate-limiting failed enrollment code attempts."""

    user            = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollment_rate_limit"
    )
    failed_attempts = models.IntegerField(default=0)
    window_start    = models.DateTimeField(null=True, blank=True)
    locked_until    = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"RateLimit(user={self.user_id}, attempts={self.failed_attempts})"


class EnrollmentCodeEvent(models.Model):
    """Append-only audit log for enrollment code lifecycle events."""

    class EventType(models.TextChoices):
        GENERATED = "generated", "Generated"
        USED      = "used",      "Used"
        REVOKED   = "revoked",   "Revoked"

    code       = models.ForeignKey(
        "EnrollmentCode", on_delete=models.CASCADE, related_name="events"
    )
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    actor      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="enrollment_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["code", "event_type"]),
        ]

    def __str__(self) -> str:
        return f"CodeEvent({self.event_type}, code={self.code_id}, actor={self.actor_id})"
