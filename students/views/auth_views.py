from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsStudent
from students.services.auth_service import (
    refresh_student_token,
    reset_password,
    send_otp,
    student_login,
    student_logout,
    student_signup,
    verify_otp,
)
from students.serializers.auth_serializers import (
    LogoutSerializer,
    ResetPasswordSerializer,
    SendOtpSerializer,
    StudentLoginSerializer,
    StudentLoginResponseSerializer,
    StudentSignupSerializer,
    StudentSignupResponseSerializer,
    TokenRefreshSerializer,
    VerifyOtpSerializer,
)


@extend_schema(
    tags=["Student Auth"],
    summary="Student signup",
    description="Register a new student account using a valid student code.",
    request=StudentSignupSerializer,
    responses={201: StudentSignupResponseSerializer},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def student_signup_view(request):
    serializer = StudentSignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    result = student_signup(**serializer.validated_data)
    return Response(result, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Student Auth"],
    summary="Student login",
    description="Authenticate student with email and password.",
    request=StudentLoginSerializer,
    responses={200: StudentLoginResponseSerializer},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def student_login_view(request):
    serializer = StudentLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    result = student_login(**serializer.validated_data)
    return Response(result)


@extend_schema(
    tags=["Student Auth"],
    summary="Refresh access token",
    description="Get a new access token using a valid refresh token.",
    request=TokenRefreshSerializer,
    responses={200: dict},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def student_token_refresh_view(request):
    serializer = TokenRefreshSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    result = refresh_student_token(serializer.validated_data["refresh_token"])
    return Response(result)


@extend_schema(
    tags=["Student Auth"],
    summary="Student logout",
    description="Revoke refresh token and close active session.",
    request=LogoutSerializer,
    responses={200: dict},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def student_logout_view(request):
    serializer = LogoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    student_logout(request.user, serializer.validated_data["refresh_token"])
    return Response({"message": "Logged out successfully"})


@extend_schema(
    tags=["Student Auth"],
    summary="Send OTP",
    description="Send a one-time password to the student's email for password reset.",
    request=SendOtpSerializer,
    responses={200: dict},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def send_otp_view(request):
    serializer = SendOtpSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    send_otp(serializer.validated_data["email"])
    return Response({"message": "OTP sent if email exists"})


@extend_schema(
    tags=["Student Auth"],
    summary="Verify OTP",
    description="Verify the OTP code and receive a password reset token.",
    request=VerifyOtpSerializer,
    responses={200: dict},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp_view(request):
    serializer = VerifyOtpSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    result = verify_otp(**serializer.validated_data)
    return Response(result)


@extend_schema(
    tags=["Student Auth"],
    summary="Reset password",
    description="Reset student password using a verified reset token.",
    request=ResetPasswordSerializer,
    responses={200: dict},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password_view(request):
    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    reset_password(**serializer.validated_data)
    return Response({"message": "Password reset successfully"})
