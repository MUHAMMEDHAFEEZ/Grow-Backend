"""
accounts/services.py — Business logic for user/auth operations.
"""
from __future__ import annotations

import uuid as _uuid_module
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from core.exceptions import Conflict, NotFound, PermissionDenied, RateLimitExceeded, ValidationError

from .models import (
    EnrollmentCode,
    EnrollmentCodeEvent,
    EnrollmentRateLimit,
    PasswordResetToken,
    School,
    SchoolMembership,
)

User = get_user_model()


def register_user(*, username: str, email: str, password: str, role: str) -> User:
    if User.objects.filter(email=email).exists():
        raise ValidationError("A user with this email already exists.")
    user = User.objects.create_user(username=username, email=email, password=password, role=role)
    return user


def login_user(*, email: str, password: str) -> dict:
    try:
        user_obj = User.objects.get(email=email)
    except User.DoesNotExist:
        raise ValidationError("Invalid credentials.")

    user = authenticate(username=user_obj.username, password=password)
    if user is None:
        raise ValidationError("Invalid credentials.")

    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        },
    }


def logout_user(*, refresh_token: str) -> None:
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except TokenError:
        raise ValidationError("Invalid or expired refresh token.")


def forgot_password(*, email: str) -> None:
    """
    Generates a password-reset token and sends it by email.
    Silently no-ops when the email is not registered (prevents user enumeration).
    """
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return  # silent — don't reveal whether email exists

    # Invalidate any outstanding tokens for this user
    PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)

    reset_token = PasswordResetToken.objects.create(user=user)

    reset_url = f"http://localhost:3000/reset-password/{reset_token.token}"
    send_mail(
        subject="Reset your Grow password",
        message=(
            f"Hi {user.username},\n\n"
            f"Click the link below to reset your password:\n{reset_url}\n\n"
            "This link expires in 24 hours. If you did not request this, ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=True,
    )


def reset_password(*, token: str, new_password: str) -> None:
    try:
        reset_token = PasswordResetToken.objects.select_related("user").get(token=token)
    except PasswordResetToken.DoesNotExist:
        raise ValidationError("Invalid or expired reset token.")

    if not reset_token.is_valid:
        raise ValidationError("This reset link has already been used or has expired.")

    reset_token.user.set_password(new_password)
    reset_token.user.save()
    reset_token.is_used = True
    reset_token.save()


def change_password(*, user: User, old_password: str, new_password: str) -> None:
    if not user.check_password(old_password):
        raise ValidationError("Current password is incorrect.")
    user.set_password(new_password)
    user.save()


def update_profile(*, user: User, **data) -> User:
    allowed_fields = {"first_name", "last_name", "phone", "avatar"}
    for field, value in data.items():
        if field in allowed_fields:
            setattr(user, field, value)
    user.save(update_fields=list(allowed_fields.intersection(data.keys())))
    return user


# ── School management ────────────────────────────────────────────────────────


def create_school(*, admin: User, name: str) -> School:
    if not admin.is_school_admin:
        raise PermissionDenied("Only school admins can create schools.")
    if School.objects.filter(created_by=admin).exists():
        raise Conflict("You already own a school.")

    with transaction.atomic():
        school = School.objects.create(created_by=admin, name=name)
        # Auto-enroll admin as a member
        SchoolMembership.objects.create(
            user=admin, school=school, role=SchoolMembership.Role.ADMIN
        )
        # Auto-generate initial pool of enrollment codes
        initial_pool = getattr(settings, "ENROLLMENT_CODE_INITIAL_POOL", 50)
        generate_enrollment_codes(school=school, quantity=initial_pool, created_by=admin)

    return school


# ── Enrollment Code Services ──────────────────────────────────────────────────


def generate_enrollment_codes(
    *, school: School, quantity: int, created_by: User
) -> list[EnrollmentCode]:
    """
    Bulk-create `quantity` unique enrollment codes for `school`.
    Creates an EnrollmentCodeEvent(GENERATED) for each code.
    """
    if quantity < 1:
        raise ValidationError("Quantity must be at least 1.")

    codes = [EnrollmentCode(school=school) for _ in range(quantity)]
    created = EnrollmentCode.objects.bulk_create(codes)

    events = [
        EnrollmentCodeEvent(
            code=code,
            event_type=EnrollmentCodeEvent.EventType.GENERATED,
            actor=created_by,
        )
        for code in created
    ]
    EnrollmentCodeEvent.objects.bulk_create(events)

    return created


def use_enrollment_code(*, code_token: str, user: User) -> SchoolMembership:
    """
    Validate and atomically consume `code_token`, enrolling `user` in the
    associated school. Enforces rate limiting, teacher one-school restriction,
    and duplicate-membership checks.
    """
    now = timezone.now()

    # ── Step 1: Rate limit check ───────────────────────────────────────────────
    rate_limit, _ = EnrollmentRateLimit.objects.get_or_create(user=user)

    if rate_limit.locked_until and rate_limit.locked_until > now:
        raise RateLimitExceeded(
            f"Too many failed attempts. Try again after {rate_limit.locked_until.isoformat()}.",
            retry_after=rate_limit.locked_until,
        )

    # Reset window if expired
    window_seconds = getattr(settings, "ENROLLMENT_RATE_LIMIT_WINDOW_SECONDS", 3600)
    if rate_limit.window_start and (now - rate_limit.window_start).total_seconds() > window_seconds:
        rate_limit.failed_attempts = 0
        rate_limit.window_start = now
        rate_limit.save(update_fields=["failed_attempts", "window_start"])

    # ── Step 2: Format validation (no rate-limit increment on format errors) ───
    try:
        _uuid_module.UUID(str(code_token))
    except (ValueError, AttributeError):
        raise ValidationError("Invalid code format.")

    # ── Helper: increment failure counter ─────────────────────────────────────
    def _fail(message: str) -> None:
        max_attempts = getattr(settings, "ENROLLMENT_RATE_LIMIT_MAX_ATTEMPTS", 10)
        lockout_seconds = getattr(settings, "ENROLLMENT_RATE_LIMIT_LOCKOUT_SECONDS", 3600)
        if not rate_limit.window_start:
            rate_limit.window_start = now
        rate_limit.failed_attempts += 1
        if rate_limit.failed_attempts >= max_attempts:
            rate_limit.locked_until = now + timedelta(seconds=lockout_seconds)
        rate_limit.save(update_fields=["failed_attempts", "window_start", "locked_until"])
        raise ValidationError(message)

    # ── Step 3: Atomic code lookup and consumption ─────────────────────────────
    class _CodeStatusError(Exception):
        def __init__(self, msg: str) -> None:
            self.msg = msg

    membership: SchoolMembership | None = None

    try:
        with transaction.atomic():
            try:
                code = EnrollmentCode.objects.select_for_update().get(token=code_token)
            except EnrollmentCode.DoesNotExist:
                raise _CodeStatusError("This code is invalid.")

            if code.status == EnrollmentCode.Status.USED:
                raise _CodeStatusError("This code has already been used.")
            if code.status == EnrollmentCode.Status.REVOKED:
                raise _CodeStatusError("This code is no longer valid.")

            # Already member — no counter increment (not a wrong code)
            if SchoolMembership.objects.filter(user=user, school=code.school).exists():
                raise ValidationError("You are already a member of this school.")

            # Teacher one-school restriction (admin role is exempt)
            if (
                user.role == "teacher"
                and SchoolMembership.objects.filter(
                    user=user, role=SchoolMembership.Role.TEACHER
                ).exists()
            ):
                raise ValidationError(
                    "You already belong to a school. "
                    "Leave your current school before joining another."
                )

            # Determine role from user.role
            _role_map = {
                "student":      SchoolMembership.Role.STUDENT,
                "teacher":      SchoolMembership.Role.TEACHER,
                "school_admin": SchoolMembership.Role.ADMIN,
            }
            membership_role = _role_map.get(user.role, SchoolMembership.Role.STUDENT)

            # Consume code
            code.status  = EnrollmentCode.Status.USED
            code.used_by = user
            code.used_at = now
            code.save(update_fields=["status", "used_by", "used_at"])

            # Create membership
            membership = SchoolMembership.objects.create(
                user=user, school=code.school, role=membership_role
            )

            # Audit event
            EnrollmentCodeEvent.objects.create(
                code=code,
                event_type=EnrollmentCodeEvent.EventType.USED,
                actor=user,
            )

            # Reset rate limit counters
            rate_limit.failed_attempts = 0
            rate_limit.locked_until    = None
            rate_limit.save(update_fields=["failed_attempts", "locked_until"])

    except _CodeStatusError as exc:
        _fail(exc.msg)

    # ── Step 4: Publish event (outside transaction) ────────────────────────────
    from core.events import EventBus, Events

    EventBus.publish(Events.SCHOOL_MEMBER_ADDED, {
        "school_id": membership.school_id,
        "user_id":   user.pk,
        "role":      membership.role,
    })

    return membership


def revoke_enrollment_code(*, code_id: int, school_id: int, admin: User) -> EnrollmentCode:
    """
    Permanently revoke an available enrollment code.
    Only the school's admin may revoke its codes.
    """
    try:
        school = School.objects.get(pk=school_id)
    except School.DoesNotExist:
        raise NotFound("School not found.")

    if school.created_by_id != admin.pk:
        raise PermissionDenied("You do not own this school.")

    try:
        code = EnrollmentCode.objects.get(pk=code_id, school=school)
    except EnrollmentCode.DoesNotExist:
        raise NotFound("Enrollment code not found.")

    if code.status == EnrollmentCode.Status.USED:
        raise ValidationError("Cannot revoke a code that has already been used.")
    if code.status == EnrollmentCode.Status.REVOKED:
        raise ValidationError("This code has already been revoked.")

    now = timezone.now()
    code.status     = EnrollmentCode.Status.REVOKED
    code.revoked_by = admin
    code.revoked_at = now
    code.save(update_fields=["status", "revoked_by", "revoked_at"])

    EnrollmentCodeEvent.objects.create(
        code=code,
        event_type=EnrollmentCodeEvent.EventType.REVOKED,
        actor=admin,
    )

    return code
