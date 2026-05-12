from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.permissions import IsTeacher
from teachers.serializers import (
    ResetPasswordSerializer,
    SendOTPSerializer,
    TeacherLoginSerializer,
    TeacherSignupSerializer,
    TokenResponseSerializer,
    VerifyOTPSerializer,
)
from teachers.services import (
    login_teacher,
    logout_teacher,
    refresh_teacher_token,
    reset_password,
    send_otp,
    signup_teacher,
    verify_otp,
)


@extend_schema(
    tags=["Teacher Auth"],
    summary="Teacher signup",
    request=TeacherSignupSerializer,
    responses={201: TokenResponseSerializer, 400: OpenApiResponse(description="Validation error."), 409: OpenApiResponse(description="Email already exists.")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request: Request) -> Response:
    serializer = TeacherSignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user, access, refresh = signup_teacher(
        school_id=serializer.validated_data["school_id"],
        full_name=serializer.validated_data["full_name"],
        email=serializer.validated_data["email"],
        password=serializer.validated_data["password"],
        teacher_code=serializer.validated_data["teacher_code"],
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    return Response(
        {"access": access, "refresh": refresh, "user_id": user.id, "role": user.role},
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    tags=["Teacher Auth"],
    summary="Teacher login",
    request=TeacherLoginSerializer,
    responses={200: TokenResponseSerializer, 400: OpenApiResponse(description="Invalid credentials.")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request: Request) -> Response:
    serializer = TeacherLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user, access, refresh = login_teacher(
        email=serializer.validated_data["email"],
        password=serializer.validated_data["password"],
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    return Response(
        {"access": access, "refresh": refresh, "user_id": user.id, "role": user.role},
    )


@extend_schema(
    tags=["Teacher Auth"],
    summary="Refresh token",
    request=None,
    responses={200: TokenResponseSerializer, 401: OpenApiResponse(description="Invalid or expired token.")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def refresh(request: Request) -> Response:
    refresh_token = request.data.get("refresh")
    if not refresh_token:
        return Response({"error": "refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
    access, new_refresh = refresh_teacher_token(refresh_token=refresh_token)
    return Response({"access": access, "refresh": new_refresh})


@extend_schema(
    tags=["Teacher Auth"],
    summary="Teacher logout",
    request=None,
    responses={200: OpenApiResponse(description="Logged out.")},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTeacher])
def logout(request: Request) -> Response:
    refresh_token = request.data.get("refresh")
    if refresh_token:
        logout_teacher(refresh_token=refresh_token)
    return Response({"detail": "Logged out."})


@extend_schema(
    tags=["Teacher Auth"],
    summary="Send OTP for password reset",
    request=SendOTPSerializer,
    responses={200: OpenApiResponse(description="OTP sent.")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def send_otp_view(request: Request) -> Response:
    serializer = SendOTPSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    result = send_otp(email=serializer.validated_data["email"])
    return Response({"detail": result})


@extend_schema(
    tags=["Teacher Auth"],
    summary="Verify OTP",
    request=VerifyOTPSerializer,
    responses={200: OpenApiResponse(description="OTP verified, reset token returned.")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp_view(request: Request) -> Response:
    serializer = VerifyOTPSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    reset_token = verify_otp(
        email=serializer.validated_data["email"],
        otp=serializer.validated_data["otp"],
    )
    return Response({"reset_token": reset_token})


@extend_schema(
    tags=["Teacher Auth"],
    summary="Reset password",
    request=ResetPasswordSerializer,
    responses={200: OpenApiResponse(description="Password reset.")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password_view(request: Request) -> Response:
    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    reset_password(
        reset_token=serializer.validated_data["reset_token"],
        new_password=serializer.validated_data["new_password"],
    )
    return Response({"detail": "Password has been reset."})
