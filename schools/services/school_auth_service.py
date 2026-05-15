from rest_framework_simplejwt.tokens import RefreshToken

from core.exceptions import ValidationError


def login_school_admin(*, username: str, password: str):
    from django.contrib.auth import authenticate, get_user_model

    User = get_user_model()
    user = authenticate(username=username, password=password)
    if user is None or not user.is_school_admin:
        raise ValidationError("Invalid credentials.")

    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user_id": user.id,
        "role": user.role,
        "username": user.username,
    }
