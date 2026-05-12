from django.conf import settings
from django.db import models


class TeacherCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    school = models.ForeignKey(
        "accounts.School", on_delete=models.CASCADE, related_name="teacher_codes"
    )
    is_used = models.BooleanField(default=False)
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="used_teacher_codes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["code", "school"])]

    def __str__(self) -> str:
        return f"TeacherCode({self.code}, school={self.school_id}, used={self.is_used})"


class TeacherProfile(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        INACTIVE = "inactive", "Inactive"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_profile",
        limit_choices_to={"role": "teacher"},
    )
    school = models.ForeignKey(
        "accounts.School",
        on_delete=models.CASCADE,
        related_name="teacher_profiles",
    )
    teacher_code = models.ForeignKey(
        TeacherCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles",
    )
    bio = models.TextField(blank=True, default="")
    avatar = models.URLField(blank=True, default="")
    preferred_language = models.CharField(
        max_length=10, default="en", blank=True
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["school", "status"]),
        ]

    def __str__(self) -> str:
        return f"TeacherProfile({self.user.username}, school={self.school_id})"


class DeviceSession(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_sessions",
        limit_choices_to={"role": "teacher"},
    )
    refresh_token_hash = models.CharField(max_length=128)
    device_info = models.CharField(max_length=255, blank=True, default="")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    last_active = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["teacher", "last_active"]),
        ]

    def __str__(self) -> str:
        return f"DeviceSession({self.teacher_id}, {self.ip_address})"


class RefreshToken(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_refresh_tokens",
        limit_choices_to={"role": "teacher"},
    )
    token_hash = models.CharField(max_length=128, db_index=True)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)
    device_info = models.CharField(max_length=255, blank=True, default="")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["teacher", "is_revoked"]),
        ]

    def __str__(self) -> str:
        return f"RefreshToken(teacher={self.teacher_id}, revoked={self.is_revoked})"


class OTPRecord(models.Model):
    email = models.EmailField()
    otp_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["email", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"OTPRecord({self.email}, used={self.is_used})"


class TeacherNotification(models.Model):
    class EventType(models.TextChoices):
        NEW_SUBMISSION = "new_submission", "New Submission"
        MISSING_ASSIGNMENT = "missing_assignment", "Missing Assignment"
        GRADE_UPDATE = "grade_update", "Grade Update"

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_notifications",
        limit_choices_to={"role": "teacher"},
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    reference_type = models.CharField(max_length=50, blank=True, default="")
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["teacher", "is_read"]),
            models.Index(fields=["teacher", "event_type", "reference_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "event_type", "reference_id"],
                name="unique_teacher_notification",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.event_type}] → {self.teacher.username}: {self.message[:50]}"


class TeacherNotificationPreference(models.Model):
    teacher = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        limit_choices_to={"role": "teacher"},
    )
    email_notifications = models.BooleanField(default=True)
    missing_assignments = models.BooleanField(default=True)
    new_submissions = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"NotificationPreference({self.teacher_id})"


class AuditLog(models.Model):
    class ActorType(models.TextChoices):
        TEACHER = "teacher", "Teacher"
        STUDENT = "student", "Student"
        ADMIN = "admin", "Admin"

    actor_type = models.CharField(max_length=10, choices=ActorType.choices)
    actor_id = models.PositiveIntegerField()
    action = models.CharField(max_length=50)
    resource_type = models.CharField(max_length=50)
    resource_id = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor_type", "actor_id"]),
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"AuditLog({self.action} {self.resource_type}#{self.resource_id} by {self.actor_type}:{self.actor_id})"
