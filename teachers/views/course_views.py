from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.permissions import IsTeacher
from teachers.serializers import (
    LessonReorderSerializer,
    TeacherCourseListSerializer,
    TeacherCourseWriteSerializer,
    TeacherLessonSerializer,
)
from teachers.selectors import (
    get_course_lessons,
    get_lesson,
    get_teacher_course_detail,
    get_teacher_courses,
)
from teachers.services import (
    create_teacher_course,
    create_teacher_lesson,
    delete_teacher_course,
    delete_teacher_lesson,
    reorder_lessons,
    update_teacher_course,
    update_teacher_lesson,
)


@extend_schema(
    tags=["Teacher Courses"],
    summary="List teacher courses",
    responses={200: TeacherCourseListSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def list_courses(request: Request) -> Response:
    courses = get_teacher_courses(request.user)
    return Response(TeacherCourseListSerializer(courses, many=True).data)


@extend_schema(
    tags=["Teacher Courses"],
    summary="Create course",
    request=TeacherCourseWriteSerializer,
    responses={201: TeacherCourseListSerializer},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTeacher])
def create_course(request: Request) -> Response:
    serializer = TeacherCourseWriteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    course = create_teacher_course(teacher=request.user, **serializer.validated_data)
    return Response(TeacherCourseListSerializer(course).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Teacher Courses"],
    summary="Get course detail",
    responses={200: TeacherCourseListSerializer, 404: OpenApiResponse(description="Not found.")},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def get_course(request: Request, course_id: int) -> Response:
    course = get_teacher_course_detail(request.user, course_id)
    if not course:
        return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(TeacherCourseListSerializer(course).data)


@extend_schema(
    tags=["Teacher Courses"],
    summary="Update course",
    request=TeacherCourseWriteSerializer,
    responses={200: TeacherCourseListSerializer},
)
@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated, IsTeacher])
def update_course(request: Request, course_id: int) -> Response:
    serializer = TeacherCourseWriteSerializer(data=request.data, partial=request.method == "PATCH")
    serializer.is_valid(raise_exception=True)
    course = update_teacher_course(teacher=request.user, course_id=course_id, **serializer.validated_data)
    return Response(TeacherCourseListSerializer(course).data)


@extend_schema(
    tags=["Teacher Courses"],
    summary="Delete course",
    responses={204: OpenApiResponse(description="Deleted.")},
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsTeacher])
def delete_course(request: Request, course_id: int) -> Response:
    delete_teacher_course(teacher=request.user, course_id=course_id)
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=["Teacher Courses"],
    summary="List course lessons",
    responses={200: TeacherLessonSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def list_lessons(request: Request, course_id: int) -> Response:
    lessons = get_course_lessons(course_id)
    return Response(TeacherLessonSerializer(lessons, many=True).data)


@extend_schema(
    tags=["Teacher Courses"],
    summary="Create lesson",
    request=TeacherLessonSerializer,
    responses={201: TeacherLessonSerializer},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTeacher])
def create_lesson(request: Request, course_id: int) -> Response:
    serializer = TeacherLessonSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    lesson = create_teacher_lesson(teacher=request.user, course_id=course_id, **serializer.validated_data)
    return Response(TeacherLessonSerializer(lesson).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Teacher Courses"],
    summary="Get lesson detail",
    responses={200: TeacherLessonSerializer, 404: OpenApiResponse(description="Not found.")},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def get_lesson_view(request: Request, lesson_id: int) -> Response:
    lesson = get_lesson(lesson_id)
    if not lesson or lesson.course.teacher_id != request.user.id:
        return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(TeacherLessonSerializer(lesson).data)


@extend_schema(
    tags=["Teacher Courses"],
    summary="Update lesson",
    request=TeacherLessonSerializer,
    responses={200: TeacherLessonSerializer},
)
@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated, IsTeacher])
def update_lesson(request: Request, lesson_id: int) -> Response:
    serializer = TeacherLessonSerializer(data=request.data, partial=request.method == "PATCH")
    serializer.is_valid(raise_exception=True)
    lesson = update_teacher_lesson(teacher=request.user, lesson_id=lesson_id, **serializer.validated_data)
    return Response(TeacherLessonSerializer(lesson).data)


@extend_schema(
    tags=["Teacher Courses"],
    summary="Delete lesson",
    responses={204: OpenApiResponse(description="Deleted.")},
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsTeacher])
def delete_lesson(request: Request, lesson_id: int) -> Response:
    delete_teacher_lesson(teacher=request.user, lesson_id=lesson_id)
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=["Teacher Courses"],
    summary="Reorder lessons",
    request=LessonReorderSerializer,
    responses={200: TeacherLessonSerializer(many=True)},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTeacher])
def reorder_lessons_view(request: Request, course_id: int) -> Response:
    serializer = LessonReorderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    lessons = reorder_lessons(
        teacher=request.user,
        course_id=course_id,
        ordered_ids=serializer.validated_data["ordered_ids"],
    )
    return Response(TeacherLessonSerializer(lessons, many=True).data)
