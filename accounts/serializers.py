import uuid as _uuid_module

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import EnrollmentCode, ParentProfile, School, SchoolMembership

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        max_length=150,
        help_text="Unique username (letters, digits, @/./+/-/_ only).",
    )
    email = serializers.EmailField(
        help_text="Valid email address. Must be unique across the platform.",
    )
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        help_text="Password (minimum 8 characters).",
    )
    role = serializers.ChoiceField(
        choices=User.Role.choices,
        help_text="User role: student | teacher | parent | school_admin.",
    )

    class Meta:
        model = User
        fields = ["username", "email", "password", "role"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data: dict) -> User:
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, help_text="Unique user ID.")
    username = serializers.CharField(help_text="Unique username.")
    email = serializers.EmailField(help_text="User's email address.")
    role = serializers.CharField(help_text="Account role: student | teacher | parent | school_admin.")
    first_name = serializers.CharField(help_text="First name.", required=False, allow_blank=True)
    last_name = serializers.CharField(help_text="Last name.", required=False, allow_blank=True)
    phone = serializers.CharField(help_text="Phone number (optional).", required=False, allow_blank=True)
    avatar = serializers.URLField(help_text="URL to profile avatar image (optional).", required=False, allow_blank=True)
    date_joined = serializers.DateTimeField(read_only=True, help_text="ISO-8601 timestamp of registration.")

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "first_name", "last_name", "phone", "avatar", "date_joined"]
        read_only_fields = ["id", "date_joined"]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Registered email address.")
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="Account password.",
    )


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField(
        help_text="JWT access token. Valid for 60 minutes. Send as `Authorization: Bearer <token>`."
    )
    refresh = serializers.CharField(
        help_text="JWT refresh token. Valid for 7 days. Use to obtain a new access token."
    )
    user = UserSerializer(help_text="Authenticated user details.")


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text="JWT refresh token to blacklist.")


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Email address associated with the account.")


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.UUIDField(help_text="Reset token received by email.")
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        help_text="New password (minimum 8 characters).",
    )


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="Current password.",
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        help_text="New password (minimum 8 characters).",
    )


class ProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=False, allow_blank=True, help_text="First name.")
    last_name = serializers.CharField(required=False, allow_blank=True, help_text="Last name.")
    phone = serializers.CharField(required=False, allow_blank=True, help_text="Phone number.")
    avatar = serializers.URLField(required=False, allow_blank=True, help_text="URL to avatar image.")

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "avatar"]


class ParentProfileSerializer(serializers.ModelSerializer):
    parent = UserSerializer(read_only=True, help_text="The parent user (set automatically).")
    child = UserSerializer(read_only=True, help_text="The linked student user.")
    child_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role="student"),
        source="child",
        write_only=True,
        help_text="ID of the student to link to this parent account.",
    )

    class Meta:
        model = ParentProfile
        fields = ["id", "parent", "child", "child_id"]
        read_only_fields = ["id", "parent"]

    def create(self, validated_data: dict) -> ParentProfile:
        validated_data["parent"] = self.context["request"].user
        return ParentProfile.objects.create(**validated_data)


class SchoolSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True, help_text="School admin who created this school.")

    class Meta:
        model = School
        fields = ["id", "name", "slug", "created_by", "created_at"]
        read_only_fields = ["id", "slug", "created_by", "created_at"]


class SchoolCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, help_text="School name.")


# ── Enrollment Code Serializers ────────────────────────────────────────────────


class UseCodeSerializer(serializers.Serializer):
    code = serializers.CharField(
        help_text="Enrollment code token (UUID format, 36 characters).",
    )

    def validate_code(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError("Invalid code format.")
        try:
            _uuid_module.UUID(str(value).strip())
        except (ValueError, AttributeError):
            raise serializers.ValidationError("Invalid code format.")
        return str(value).strip()


class _BriefUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class _BriefSchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ["id", "name", "slug"]


class MembershipSerializer(serializers.ModelSerializer):
    school = _BriefSchoolSerializer(read_only=True)

    class Meta:
        model = SchoolMembership
        fields = ["school", "role", "joined_at"]


class EnrollmentCodeSerializer(serializers.ModelSerializer):
    used_by    = _BriefUserSerializer(read_only=True)
    revoked_by = _BriefUserSerializer(read_only=True)

    class Meta:
        model = EnrollmentCode
        fields = [
            "id", "token", "status",
            "used_by", "used_at",
            "revoked_by", "revoked_at",
            "created_at",
        ]
        read_only_fields = fields


class GenerateCodesSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        min_value=1,
        help_text="Number of enrollment codes to generate (must be ≥ 1).",
    )
