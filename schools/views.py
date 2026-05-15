from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsSchoolAdmin
from schools.models import School
from schools.selectors import get_grades_for_school
from schools.serializers import (
    GradeSerializer,
    SchoolLoginSerializer,
    SchoolLoginResponseSerializer,
    SchoolSerializer,
)
from schools.services.school_auth_service import login_school_admin
from students.selectors import get_students_by_school
from students.serializers.school_student_serializers import SchoolStudentListSerializer


class GradeListView(ListAPIView):
    serializer_class = GradeSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        school_id = self.request.query_params.get("school_id")
        return get_grades_for_school(school_id=int(school_id) if school_id else None)


class SchoolListView(ListAPIView):
    queryset = School.objects.all().order_by("name")
    serializer_class = SchoolSerializer
    permission_classes = [AllowAny]


class StudentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _get_admin_school(user):
    """Resolve school_admin user to their schools.School instance.

    Uses the email domain prefix (e.g. admin@ELOBOUR.edu -> ELOBOUR)
    to match the school name. Falls back to accounts.School.owned_school
    if that record exists.
    """
    try:
        accounts_school = user.owned_school
        return School.objects.get(name=accounts_school.name)
    except Exception:
        pass
    domain_prefix = user.email.split("@")[1].split(".")[0].upper()
    return School.objects.get(name=domain_prefix)


@extend_schema(
    tags=["School Admin"],
    summary="List students in admin's school",
    description="Returns a paginated list of all students registered in the authenticated school admin's school.",
    responses={200: SchoolStudentListSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def school_student_list_view(request):
    try:
        school = _get_admin_school(request.user)
    except School.DoesNotExist:
        return Response(
            {"detail": "No school associated with your account."},
            status=status.HTTP_403_FORBIDDEN,
        )
    students = get_students_by_school(school.id)
    paginator = StudentPagination()
    page = paginator.paginate_queryset(students, request)
    serializer = SchoolStudentListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@extend_schema(
    tags=["School Auth"],
    summary="School admin login",
    description=(
        "Dedicated login endpoint for school administrators. "
        "School accounts are pre-seeded and do NOT signup through this endpoint. "
        "This auth flow is completely separate from student/teacher/parent authentication."
    ),
    request=SchoolLoginSerializer,
    responses={
        200: SchoolLoginResponseSerializer,
        400: OpenApiResponse(description="Invalid credentials."),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def school_login_view(request):
    serializer = SchoolLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    result = login_school_admin(**serializer.validated_data)
    return Response(result, status=status.HTTP_200_OK)
