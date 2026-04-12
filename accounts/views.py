"""
accounts/views.py — Auth, profile, and school admin endpoints.
"""
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.exceptions import NotFound, PermissionDenied, RateLimitExceeded, ValidationError
from core.permissions import IsParent, IsSchoolAdmin

from .selectors import get_enrollment_codes_for_school, get_school_for_admin
from .serializers import (
    ChangePasswordSerializer,
    EnrollmentCodeSerializer,
    ForgotPasswordSerializer,
    GenerateCodesSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    LogoutSerializer,
    MembershipSerializer,
    ParentProfileSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    SchoolCreateSerializer,
    SchoolSerializer,
    UseCodeSerializer,
    UserSerializer,
)
from .services import (
    change_password,
    create_school,
    forgot_password,
    generate_enrollment_codes,
    login_user,
    logout_user,
    reset_password,
    revoke_enrollment_code,
    update_profile,
    use_enrollment_code,
)


# ── Register ──────────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Auth"],
    summary="Register a new account",
    description=(
        "Create a new user account. The `role` field determines access level:\n\n"
        "- **student** — enroll in courses, submit assignments, view own grades\n"
        "- **teacher** — create courses, post assignments, grade submissions\n"
        "- **parent** — view a linked child's grades, attendance, and notifications\n"
        "- **school_admin** — manage a school, add teachers, oversee courses\n\n"
        "Returns the created user profile. Call `/auth/login/` to obtain tokens."
    ),
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(response=UserSerializer, description="Account created successfully."),
        400: OpenApiResponse(description="Validation error (duplicate email, weak password, etc.)."),
    },
    examples=[
        OpenApiExample(
            "Student Registration",
            value={"username": "sara_student", "email": "sara@school.edu", "password": "SecurePass123", "role": "student"},
            request_only=True,
        ),
        OpenApiExample(
            "School Admin Registration",
            value={"username": "admin_ali", "email": "ali@school.edu", "password": "AdminPass456", "role": "school_admin"},
            request_only=True,
        ),
    ],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request: Request) -> Response:
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


# ── Login ─────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Auth"],
    summary="Login — obtain JWT tokens",
    description=(
        "Authenticate with email and password. Returns:\n\n"
        "- `access` — short-lived JWT (60 min). Send as `Authorization: Bearer <token>`.\n"
        "- `refresh` — long-lived JWT (7 days). Use `POST /auth/token/refresh/` to renew.\n\n"
        "Click the **Authorize** button at the top and paste the `access` token to "
        "authenticate all subsequent requests in Swagger UI."
    ),
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(response=LoginResponseSerializer, description="Login successful."),
        400: OpenApiResponse(description="Invalid credentials."),
    },
    examples=[
        OpenApiExample(
            "Login",
            value={"email": "sara@school.edu", "password": "SecurePass123"},
            request_only=True,
        ),
        OpenApiExample(
            "Login Response",
            value={
                "access": "eyJhbGciOiJIUzI1NiIsInR5...",
                "refresh": "eyJhbGciOiJIUzI1NiIsInR5...",
                "user": {"id": 3, "username": "sara_student", "email": "sara@school.edu", "role": "student"},
            },
            response_only=True,
        ),
    ],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request: Request) -> Response:
    email = request.data.get("email", "")
    password = request.data.get("password", "")
    data = login_user(email=email, password=password)
    return Response(data)


# ── Logout ────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Auth"],
    summary="Logout — invalidate refresh token",
    description=(
        "Blacklists the provided refresh token, preventing it from being used to issue "
        "new access tokens. The current access token remains valid until it expires (60 min). "
        "Call this on logout from the client."
    ),
    request=LogoutSerializer,
    responses={
        204: OpenApiResponse(description="Logged out successfully."),
        400: OpenApiResponse(description="Invalid or already-used refresh token."),
    },
    examples=[
        OpenApiExample("Logout", value={"refresh": "eyJhbGciOiJIUzI1NiIsInR5..."}, request_only=True),
    ],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request: Request) -> Response:
    serializer = LogoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    logout_user(refresh_token=serializer.validated_data["refresh"])
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── Forgot password ───────────────────────────────────────────────────────────

@extend_schema(
    tags=["Auth"],
    summary="Request a password reset link",
    description=(
        "Sends a password-reset link to the given email address if an account exists. "
        "The link contains a one-time token valid for **24 hours**. "
        "Always returns 200 to prevent user-enumeration attacks."
    ),
    request=ForgotPasswordSerializer,
    responses={200: OpenApiResponse(description="Reset email sent (if account exists).")},
    examples=[
        OpenApiExample("Forgot Password", value={"email": "sara@school.edu"}, request_only=True),
    ],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password_view(request: Request) -> Response:
    serializer = ForgotPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    forgot_password(email=serializer.validated_data["email"])
    return Response({"detail": "If an account with that email exists, a reset link has been sent."})


# ── Reset password ────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Auth"],
    summary="Reset password using a token",
    description=(
        "Sets a new password using the token from the reset email. "
        "Each token can only be used once and expires after 24 hours."
    ),
    request=ResetPasswordSerializer,
    responses={
        200: OpenApiResponse(description="Password updated successfully."),
        400: OpenApiResponse(description="Token invalid, expired, or already used."),
    },
    examples=[
        OpenApiExample(
            "Reset Password",
            value={"token": "550e8400-e29b-41d4-a716-446655440000", "new_password": "NewSecurePass99"},
            request_only=True,
        ),
    ],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password_view(request: Request) -> Response:
    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    reset_password(
        token=str(serializer.validated_data["token"]),
        new_password=serializer.validated_data["new_password"],
    )
    return Response({"detail": "Password has been reset successfully."})


# ── Change password ───────────────────────────────────────────────────────────

@extend_schema(
    tags=["Auth"],
    summary="Change password (authenticated)",
    description="Change the current user's password. Requires the existing password for verification.",
    request=ChangePasswordSerializer,
    responses={
        200: OpenApiResponse(description="Password changed successfully."),
        400: OpenApiResponse(description="Old password incorrect or new password too weak."),
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password_view(request: Request) -> Response:
    serializer = ChangePasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    change_password(
        user=request.user,
        old_password=serializer.validated_data["old_password"],
        new_password=serializer.validated_data["new_password"],
    )
    return Response({"detail": "Password changed successfully."})


# ── Profile ───────────────────────────────────────────────────────────────────

@extend_schema(
    methods=["GET"],
    tags=["Auth"],
    summary="Get current user profile",
    description="Returns the full profile of the currently authenticated user.",
    responses={
        200: OpenApiResponse(response=UserSerializer, description="Current user data."),
        401: OpenApiResponse(description="Not authenticated."),
    },
)
@extend_schema(
    methods=["PUT"],
    tags=["Auth"],
    summary="Update profile",
    description=(
        "Update the authenticated user's profile fields. All fields are optional — "
        "only the fields you include will be updated."
    ),
    request=ProfileUpdateSerializer,
    responses={
        200: OpenApiResponse(response=UserSerializer, description="Updated profile."),
        400: OpenApiResponse(description="Validation error."),
    },
    examples=[
        OpenApiExample(
            "Update Profile",
            value={"first_name": "Sara", "last_name": "Ali", "phone": "+201234567890", "avatar": "https://cdn.example.com/avatars/sara.jpg"},
            request_only=True,
        ),
    ],
)
@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def profile(request: Request) -> Response:
    if request.method == "GET":
        return Response(UserSerializer(request.user).data)

    serializer = ProfileUpdateSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    user = update_profile(user=request.user, **serializer.validated_data)
    return Response(UserSerializer(user).data)


# ── Me (kept for backwards compatibility) ─────────────────────────────────────

@extend_schema(
    tags=["Auth"],
    summary="Get current user (alias for GET /auth/profile/)",
    description="Returns the profile of the currently authenticated user.",
    responses={
        200: OpenApiResponse(response=UserSerializer, description="Current user data."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
    },
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request: Request) -> Response:
    return Response(UserSerializer(request.user).data)


# ── Parent profile ─────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Auth"],
    summary="Link parent to a student child",
    description=(
        "Allows a **parent** account to link itself to a student account. "
        "Once linked, the parent can view the student's grades, attendance, and notifications.\n\n"
        "A parent can currently be linked to one child (MVP constraint)."
    ),
    request=ParentProfileSerializer,
    responses={
        201: OpenApiResponse(response=ParentProfileSerializer, description="Profile linked successfully."),
        400: OpenApiResponse(description="Validation error (e.g. child_id is not a student)."),
        403: OpenApiResponse(description="Only parents can use this endpoint."),
    },
    examples=[
        OpenApiExample("Link Child", value={"child_id": 5}, request_only=True),
    ],
)
class ParentProfileView(generics.CreateAPIView):
    """POST /auth/parent-profile/ — parent links themselves to a child."""
    serializer_class = ParentProfileSerializer
    permission_classes = [IsParent]

    def get_queryset(self):
        return []


# ── School (School Admin) ──────────────────────────────────────────────────────

@extend_schema(
    methods=["POST"],
    tags=["Auth"],
    summary="Create a school",
    description=(
        "**School admins only.** Creates a new school owned by the calling school admin. "
        "Each admin can own exactly one school. "
        "A URL-friendly `slug` is auto-generated from the school name."
    ),
    request=SchoolCreateSerializer,
    responses={
        201: OpenApiResponse(response=SchoolSerializer, description="School created."),
        400: OpenApiResponse(description="Validation error."),
        403: OpenApiResponse(description="Only school admins can create schools."),
        409: OpenApiResponse(description="You already own a school."),
    },
    examples=[
        OpenApiExample("Create School", value={"name": "Al-Nour International School"}, request_only=True),
    ],
)
@extend_schema(
    methods=["GET"],
    tags=["Auth"],
    summary="Get my school",
    description="**School admins only.** Returns the school owned by the authenticated admin.",
    responses={
        200: OpenApiResponse(response=SchoolSerializer, description="School details."),
        404: OpenApiResponse(description="No school found for this admin."),
    },
)
@api_view(["GET", "POST"])
@permission_classes([IsSchoolAdmin])
def school_view(request: Request) -> Response:
    if request.method == "GET":
        school = get_school_for_admin(request.user)
        if school is None:
            return Response({"error": "No school found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(SchoolSerializer(school).data)

    serializer = SchoolCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    school = create_school(admin=request.user, name=serializer.validated_data["name"])
    return Response(SchoolSerializer(school).data, status=status.HTTP_201_CREATED)


# ── Enrollment Code Endpoints ─────────────────────────────────────────────────

from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter


@extend_schema(
    tags=["Enrollment"],
    summary="Use an enrollment code",
    description=(
        "Submit a single-use enrollment code to join the associated school. "
        "The code is atomically consumed on success. "
        "Failed attempts (wrong code, used code, revoked code) count toward the rate limit."
    ),
    request=UseCodeSerializer,
    responses={
        201: OpenApiResponse(response=MembershipSerializer, description="Enrolled successfully."),
        400: OpenApiResponse(description="Invalid, used, revoked code, or business rule violation."),
        401: OpenApiResponse(description="Authentication required."),
        429: OpenApiResponse(description="Rate limit exceeded."),
    },
)
class UseCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = UseCodeSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response({"error": str(first_error)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            membership = use_enrollment_code(
                code_token=serializer.validated_data["code"],
                user=request.user,
            )
        except RateLimitExceeded as exc:
            return Response(
                {
                    "error": str(exc.detail),
                    "retry_after": exc.retry_after.isoformat() if exc.retry_after else None,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except (ValidationError, PermissionDenied) as exc:
            return Response({"error": str(exc.detail)}, status=exc.status_code)

        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Enrollment"],
    summary="List enrollment codes for a school",
    description=(
        "**School admins only.** Returns a paginated list of all enrollment codes for the "
        "caller's school, including status, usage details, and revocation details."
    ),
    responses={
        200: OpenApiResponse(response=EnrollmentCodeSerializer(many=True), description="Paginated code list."),
        403: OpenApiResponse(description="Not the school's admin."),
        404: OpenApiResponse(description="School not found."),
    },
)
class EnrollmentCodeListView(APIView):
    permission_classes = [IsAuthenticated, IsSchoolAdmin]

    def get(self, request: Request, school_id: int) -> Response:
        try:
            qs = get_enrollment_codes_for_school(school_id=school_id, admin=request.user)
        except (NotFound, PermissionDenied) as exc:
            return Response({"error": str(exc.detail)}, status=exc.status_code)

        # Filter by status
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        # Ordering
        ordering = request.query_params.get("ordering", "-created_at")
        allowed_orderings = {"created_at", "-created_at", "status", "-status"}
        if ordering in allowed_orderings:
            qs = qs.order_by(ordering)

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)
        serializer = EnrollmentCodeSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


@extend_schema(
    tags=["Enrollment"],
    summary="Generate additional enrollment codes",
    description=(
        "**School admins only.** Generates a batch of additional single-use enrollment "
        "codes for the school. No upper limit on quantity."
    ),
    request=GenerateCodesSerializer,
    responses={
        201: OpenApiResponse(description="Codes generated."),
        400: OpenApiResponse(description="Invalid quantity."),
        403: OpenApiResponse(description="Not the school's admin."),
        404: OpenApiResponse(description="School not found."),
    },
)
class GenerateCodesView(APIView):
    permission_classes = [IsAuthenticated, IsSchoolAdmin]

    def post(self, request: Request, school_id: int) -> Response:
        serializer = GenerateCodesSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from .models import School
            school = School.objects.get(pk=school_id)
        except Exception:
            return Response({"error": "School not found."}, status=status.HTTP_404_NOT_FOUND)

        if school.created_by_id != request.user.pk:
            return Response({"error": "You do not own this school."}, status=status.HTTP_403_FORBIDDEN)

        quantity = serializer.validated_data["quantity"]
        try:
            codes = generate_enrollment_codes(school=school, quantity=quantity, created_by=request.user)
        except ValidationError as exc:
            return Response({"error": str(exc.detail)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"generated": len(codes), "codes": EnrollmentCodeSerializer(codes, many=True).data},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Enrollment"],
    summary="Revoke an enrollment code",
    description=(
        "**School admins only.** Permanently revokes an available (unused) enrollment code. "
        "Revoked codes cannot be enrolled with."
    ),
    responses={
        200: OpenApiResponse(response=EnrollmentCodeSerializer, description="Code revoked."),
        400: OpenApiResponse(description="Code already used or revoked."),
        403: OpenApiResponse(description="Not the school's admin."),
        404: OpenApiResponse(description="School or code not found."),
    },
)
class RevokeCodeView(APIView):
    permission_classes = [IsAuthenticated, IsSchoolAdmin]
    serializer_class = EnrollmentCodeSerializer  # hint for drf-spectacular

    def post(self, request: Request, school_id: int, code_id: int) -> Response:
        try:
            code = revoke_enrollment_code(
                code_id=code_id, school_id=school_id, admin=request.user
            )
        except (NotFound, PermissionDenied) as exc:
            return Response({"error": str(exc.detail)}, status=exc.status_code)
        except ValidationError as exc:
            return Response({"error": str(exc.detail)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(EnrollmentCodeSerializer(code).data, status=status.HTTP_200_OK)
