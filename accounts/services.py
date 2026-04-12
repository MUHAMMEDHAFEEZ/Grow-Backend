"""
accounts/services.py — Business logic for user/auth operations.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.mail import send_mail
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from core.exceptions import Conflict, NotFound, ValidationError

from .models import PasswordResetToken, School

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
        from core.exceptions import PermissionDenied
        raise PermissionDenied("Only school admins can create schools.")
    if School.objects.filter(created_by=admin).exists():
        raise Conflict("You already own a school.")
    return School.objects.create(created_by=admin, name=name)
