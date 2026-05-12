import random
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from core.exceptions import RateLimitExceeded, ValidationError
from students.models import LoginHistory, OTPRecord, RefreshToken as StudentRefreshToken, Student, StudentSession

User = get_user_model()


# ── Rate Limiting ──────────────────────────────────────────────────────────────


def _check_rate_limit(key, max_attempts, window_seconds, block_seconds=None):
    now = timezone.now()
    cache_key = f"student_rate_limit:{key}"
    data = cache.get(cache_key)

    if data is None:
        cache.set(cache_key, {"count": 1, "window_start": now.timestamp()}, window_seconds)
        return

    window_start = timezone.datetime.fromtimestamp(data["window_start"], tz=now.tzinfo)
    if (now - window_start).total_seconds() > window_seconds:
        cache.set(cache_key, {"count": 1, "window_start": now.timestamp()}, window_seconds)
        return

    data["count"] += 1
    if data["count"] > max_attempts:
        if block_seconds:
            cache.set(cache_key + ":blocked", True, block_seconds)
            raise RateLimitExceeded("Too many attempts. Try again later.")
        raise RateLimitExceeded("Too many attempts. Try again later.")

    cache.set(cache_key, data, window_seconds)


def _is_blocked(key):
    return cache.get(f"student_rate_limit:{key}:blocked") is not None


# ── Auth Services ──────────────────────────────────────────────────────────────


def student_signup(school_id, full_name, email, password, student_code):
    if User.objects.filter(email=email).exists():
        raise ValidationError("A user with this email already exists.")

    try:
        student = Student.objects.get(student_id=student_code, user__isnull=True)
    except Student.DoesNotExist:
        raise ValidationError("Invalid or already claimed student code.")

    username = f"student_{email.split('@')[0]}_{secrets.token_hex(4)}"
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        role="student",
    )
    student.user = user
    student.save(update_fields=["user"])

    refresh = RefreshToken.for_user(user)
    StudentSession.objects.create(student=user, is_active=True)

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
        },
        "student": {
            "id": student.id,
            "full_name": student.full_name,
            "student_id": student.student_id,
        },
    }


def student_login(school_id, email, password):
    if _is_blocked(f"login:{email}"):
        raise RateLimitExceeded("Too many login attempts. Try again later.")
    _check_rate_limit(f"login:{email}", 10, 3600, 3600)

    try:
        user_obj = User.objects.get(email=email, role="student")
    except User.DoesNotExist:
        raise ValidationError("Invalid credentials.")

    user = authenticate(username=user_obj.username, password=password)
    if user is None:
        raise ValidationError("Invalid credentials.")

    today = timezone.now().date()
    LoginHistory.objects.get_or_create(student=user, login_date=today)

    StudentSession.objects.filter(student=user, is_active=True).update(is_active=False)
    session = StudentSession.objects.create(student=user, is_active=True)

    StudentRefreshToken.objects.filter(student=user, is_revoked=False).update(is_revoked=True)

    refresh = RefreshToken.for_user(user)

    student_ref = StudentRefreshToken.objects.create(
        student=user,
        token=str(refresh),
        expires_at=timezone.now() + timedelta(days=30),
    )

    student_profile = getattr(user, "student_profile", None)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
        },
        "student": {
            "full_name": student_profile.full_name if student_profile else None,
            "student_id": student_profile.student_id if student_profile else None,
        },
    }


def refresh_student_token(refresh_token_str):
    try:
        stored_token = StudentRefreshToken.objects.get(
            token=refresh_token_str, is_revoked=False
        )
    except StudentRefreshToken.DoesNotExist:
        raise ValidationError("Invalid or revoked refresh token.")

    if timezone.now() >= stored_token.expires_at:
        stored_token.is_revoked = True
        stored_token.save(update_fields=["is_revoked"])
        raise ValidationError("Refresh token has expired.")

    try:
        refresh = RefreshToken(refresh_token_str)
        return {"access": str(refresh.access_token)}
    except Exception:
        raise ValidationError("Invalid refresh token.")


def student_logout(student, refresh_token_str=None):
    if refresh_token_str:
        StudentRefreshToken.objects.filter(
            student=student, token=refresh_token_str, is_revoked=False
        ).update(is_revoked=True)

    student_session = StudentSession.objects.filter(
        student=student, is_active=True
    ).order_by("-login_time").first()

    if student_session:
        now = timezone.now()
        student_session.logout_time = now
        student_session.duration = int((now - student_session.login_time).total_seconds())
        student_session.is_active = False
        student_session.save(update_fields=["logout_time", "duration", "is_active"])

    try:
        refresh = RefreshToken(refresh_token_str)
        refresh.blacklist()
    except Exception:
        pass


def send_otp(email):
    if _is_blocked(f"otp_send:{email}"):
        raise RateLimitExceeded("Too many OTP requests. Try again later.")
    _check_rate_limit(f"otp_send:{email}", 5, 3600, 3600)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return

    OTPRecord.objects.filter(email=email, is_used=False).update(is_used=True)

    otp_code = str(random.randint(100000, 999999))
    hashed = make_password(otp_code)

    OTPRecord.objects.create(
        email=email,
        otp_code=hashed,
        expires_at=timezone.now() + timedelta(minutes=10),
    )

    send_mail(
        subject="Your OTP Code",
        message=f"Your OTP code is: {otp_code}\nThis code expires in 10 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=True,
    )


def verify_otp(email, otp_code):
    if _is_blocked(f"otp_verify:{email}"):
        raise RateLimitExceeded("Too many verification attempts. Try again later.")
    _check_rate_limit(f"otp_verify:{email}", 5, 3600, 3600)

    otp_records = OTPRecord.objects.filter(email=email, is_used=False).order_by("-created_at")

    for record in otp_records:
        if record.is_expired:
            record.is_used = True
            record.save(update_fields=["is_used"])
            continue

        if check_password(otp_code, record.otp_code):
            record.is_used = True
            record.save(update_fields=["is_used"])

            reset_token = secrets.token_urlsafe(32)
            cache.set(f"password_reset_token:{reset_token}", email, 600)
            return {"reset_token": reset_token}

    raise ValidationError("Invalid or expired OTP code.")


def reset_password(reset_token, new_password):
    email = cache.get(f"password_reset_token:{reset_token}")
    if email is None:
        raise ValidationError("Invalid or expired reset token.")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        raise ValidationError("User not found.")

    user.set_password(new_password)
    user.save(update_fields=["password"])

    StudentRefreshToken.objects.filter(student=user, is_revoked=False).update(is_revoked=True)

    cache.delete(f"password_reset_token:{reset_token}")
