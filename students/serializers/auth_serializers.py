from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers


@extend_schema_serializer(component_name="StudentSignupRequest")
class StudentSignupSerializer(serializers.Serializer):
    school_id = serializers.IntegerField(required=True)
    full_name = serializers.CharField(required=True, max_length=150)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True, min_length=8)
    student_code = serializers.CharField(required=True)


class StudentSignupResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = serializers.DictField()
    student = serializers.DictField()


@extend_schema_serializer(component_name="StudentLoginRequest")
class StudentLoginSerializer(serializers.Serializer):
    school_id = serializers.IntegerField(required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class StudentLoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = serializers.DictField()
    student = serializers.DictField()


@extend_schema_serializer(component_name="StudentTokenRefreshRequest")
class TokenRefreshSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True)


@extend_schema_serializer(component_name="StudentLogoutRequest")
class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True)


@extend_schema_serializer(component_name="StudentSendOtpRequest")
class SendOtpSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


@extend_schema_serializer(component_name="StudentVerifyOtpRequest")
class VerifyOtpSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(required=True)


@extend_schema_serializer(component_name="StudentResetPasswordRequest")
class ResetPasswordSerializer(serializers.Serializer):
    reset_token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
