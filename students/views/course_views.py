from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsStudent
from students.selectors import get_course_detail, get_courses_for_student
from students.serializers.course_serializers import (
    CourseDetailSerializer,
    CourseListSerializer,
)
from students.services.progress_service import complete_lesson


@extend_schema(
    tags=["Student Courses"],
    summary="List courses",
    description="Get courses for the student, with optional status filter.",
    responses={200: CourseListSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStudent])
def student_course_list_view(request):
    filter_status = request.query_params.get("filter", "all")
    courses = get_courses_for_student(request.user, filter_status)
    serializer = CourseListSerializer(courses, many=True)
    return Response(serializer.data)


@extend_schema(
    tags=["Student Courses"],
    summary="Course detail",
    description="Get full course content with lesson completion status.",
    responses={200: CourseDetailSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStudent])
def student_course_detail_view(request, course_id):
    data = get_course_detail(course_id, request.user)
    serializer = CourseDetailSerializer(data)
    return Response(serializer.data)


@extend_schema(
    tags=["Student Courses"],
    summary="Complete lesson",
    description="Mark a lesson as completed.",
    request=None,
    responses={200: dict},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def complete_lesson_view(request, lesson_id):
    result = complete_lesson(request.user, lesson_id)
    return Response(result)
