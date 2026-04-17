"""
courses/views.py — Course, Lesson, and Enrollment endpoints.
"""

from drf_spectacular.openapi import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from assignments.views import AssignmentViewSet

from core.permissions import IsStudent, IsTeacher
from submissions.views import SubmissionViewSet

from . import selectors, services
from .serializers import (
    AttendanceResultSerializer,
    CourseSerializer,
    CourseWriteSerializer,
    EnrollmentSerializer,
    LessonAttendanceSummarySerializer,
    LessonSerializer,
)


_COURSE_PK_PARAM = OpenApiParameter(
    name="id",
    type=OpenApiTypes.INT,
    location=OpenApiParameter.PATH,
    description="Unique course ID.",
)


class CourseViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == "lessons" and self.request.method in (
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        ):
            return [IsTeacher()]
        return [IsAuthenticated()]

    @extend_schema(
        tags=["Courses"],
        summary="List courses",
        description=(
            "Returns courses scoped to the caller's role:\n\n"
            "- **Teacher** → courses they own\n"
            "- **Student** → courses they are enrolled in\n"
            "- **Parent** → all courses (read-only overview)\n"
        ),
        responses={200: CourseSerializer(many=True)},
    )
    def list(self, request: Request) -> Response:
        user = request.user
        if user.is_teacher:
            qs = selectors.get_courses_for_teacher(user)
        elif user.is_student:
            qs = selectors.get_enrolled_courses(user)
        else:
            qs = selectors.get_all_courses()
        return Response(CourseSerializer(qs, many=True).data)

    @extend_schema(
        tags=["Courses"],
        summary="Get course details",
        parameters=[_COURSE_PK_PARAM],
        description="Retrieve full details for a single course by its ID.",
        responses={
            200: CourseSerializer,
            404: OpenApiResponse(description="Course not found."),
        },
    )
    def retrieve(self, request: Request, pk: int = None) -> Response:
        qs = selectors.get_all_courses().filter(pk=pk)
        if not qs.exists():
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CourseSerializer(qs.first()).data)

    @extend_schema(
        tags=["Courses"],
        summary="Create a new course",
        description=(
            "**Teachers only.** Creates a new course owned by the calling teacher. "
            "After creation, students can enroll using the `/courses/{id}/enroll/` endpoint."
        ),
        request=CourseWriteSerializer,
        responses={
            201: OpenApiResponse(
                response=CourseSerializer, description="Course created."
            ),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Only teachers can create courses."),
        },
        examples=[
            OpenApiExample(
                "Create Course",
                value={
                    "title": "Biology — Grade 10",
                    "description": "Topics: cells, genetics, ecosystems.",
                },
                request_only=True,
            ),
        ],
    )
    def create(self, request: Request) -> Response:
        serializer = CourseWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = services.create_course(
            teacher=request.user, **serializer.validated_data
        )
        return Response(CourseSerializer(course).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Courses"],
        summary="Update a course",
        parameters=[_COURSE_PK_PARAM],
        description="**Teachers only.** Partially or fully update a course you own.",
        request=CourseWriteSerializer,
        responses={
            200: CourseSerializer,
            403: OpenApiResponse(description="You do not own this course."),
            404: OpenApiResponse(description="Course not found."),
        },
    )
    def update(self, request: Request, pk: int = None) -> Response:
        serializer = CourseWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        course = services.update_course(
            course_id=pk, teacher=request.user, **serializer.validated_data
        )
        return Response(CourseSerializer(course).data)

    @extend_schema(
        tags=["Courses"],
        summary="Delete a course",
        parameters=[_COURSE_PK_PARAM],
        description="**Teachers only.** Permanently deletes a course and all its lessons and assignments.",
        responses={
            204: OpenApiResponse(description="Deleted successfully."),
            403: OpenApiResponse(description="You do not own this course."),
            404: OpenApiResponse(description="Course not found."),
        },
    )
    def destroy(self, request: Request, pk: int = None) -> Response:
        services.delete_course(course_id=pk, teacher=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=["Courses"],
        summary="Enroll in a course",
        parameters=[_COURSE_PK_PARAM],
        description=(
            "**Students only.** Enroll the authenticated student in the course. "
            "An `enrollment_created` notification is sent to the student upon success."
        ),
        request=None,
        responses={
            201: OpenApiResponse(
                response=EnrollmentSerializer, description="Enrolled successfully."
            ),
            403: OpenApiResponse(description="Only students can enroll."),
            404: OpenApiResponse(description="Course not found."),
            409: OpenApiResponse(description="Already enrolled in this course."),
        },
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def enroll(self, request: Request, pk: int = None) -> Response:
        enrollment = services.enroll_student(course_id=pk, student=request.user)
        return Response(
            EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        tags=["Courses"],
        summary="List enrolled students",
        parameters=[_COURSE_PK_PARAM],
        description="**Teachers only.** Returns all students currently enrolled in this course.",
        responses={200: EnrollmentSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], permission_classes=[IsTeacher])
    def students(self, request: Request, pk: int = None) -> Response:
        enrollments = selectors.get_course_students(course_id=pk)
        return Response(EnrollmentSerializer(enrollments, many=True).data)

    @extend_schema(
        methods=["GET"],
        tags=["Lessons"],
        summary="List lessons in a course",
        parameters=[_COURSE_PK_PARAM],
        description="Returns all lessons for the course, ordered by their `order` field.",
        responses={200: LessonSerializer(many=True)},
    )
    @extend_schema(
        methods=["POST"],
        tags=["Lessons"],
        summary="Create a lesson",
        parameters=[_COURSE_PK_PARAM],
        description=(
            "**Teachers only.** Adds a new lesson to the course. "
            "Set `order` to control where the lesson appears in the sequence."
        ),
        request=LessonSerializer,
        responses={
            201: OpenApiResponse(
                response=LessonSerializer, description="Lesson created."
            ),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="You do not own this course."),
        },
        examples=[
            OpenApiExample(
                "Create Lesson",
                value={
                    "title": "Chapter 1: The Cell",
                    "content": "A cell is the basic unit of life...",
                    "order": 1,
                },
                request_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["get", "post"])
    def lessons(self, request: Request, pk: int = None) -> Response:
        if request.method == "GET":
            lessons = selectors.get_lessons_for_course(course_id=pk)
            return Response(LessonSerializer(lessons, many=True).data)

        serializer = LessonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson = services.create_lesson(
            course_id=pk, teacher=request.user, **serializer.validated_data
        )
        return Response(LessonSerializer(lesson).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Lessons"],
        summary="Join a lesson",
        description=(
            "**Students only.** Automatically marks attendance when a student joins a lesson. "
            "Status is calculated based on server time:\n"
            "- Present: joins within 10 minutes of start time\n"
            "- Late: joins after grace period but before lesson ends\n"
            "- Absent: joins after lesson ends\n"
            "- Rejected: joins before lesson starts"
        ),
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Unique lesson ID.",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=AttendanceResultSerializer,
                description="Attendance marked successfully.",
            ),
            400: OpenApiResponse(description="Cannot join before lesson starts."),
            403: OpenApiResponse(description="Not enrolled in this course."),
            404: OpenApiResponse(description="Lesson not found."),
        },
    )
    @action(detail=True, methods=["post"], permission_classes=[IsStudent])
    def join(self, request: Request, pk: int = None) -> Response:
        result = services.join_lesson(lesson_id=pk, student=request.user)
        return Response(AttendanceResultSerializer(result).data)

    @extend_schema(
        tags=["Lessons"],
        summary="Get lesson attendance",
        description=(
            "**Teachers only.** Returns attendance status for all enrolled students in a lesson."
        ),
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Unique lesson ID.",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=LessonAttendanceSummarySerializer,
                description="Lesson attendance summary.",
            ),
            403: OpenApiResponse(
                description="You do not have permission to view this attendance."
            ),
            404: OpenApiResponse(description="Lesson not found."),
        },
    )
    @action(detail=True, methods=["get"], permission_classes=[IsTeacher])
    def attendance(self, request: Request, pk: int = None) -> Response:
        summary = services.get_lesson_attendance_summary(
            lesson_id=pk, teacher=request.user
        )
        return Response(LessonAttendanceSummarySerializer(summary).data)


class LessonViewSet(viewsets.ViewSet):
    """
    ViewSet for lesson-specific actions that operate directly on lesson ID.
    Routes: /lessons/{id}/join/, /lessons/{id}/attendance/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Lessons"],
        summary="Join a lesson",
        description=(
            "**Students only.** Automatically marks attendance when a student joins a lesson. "
            "Status is calculated based on server time:\n"
            "- Present: joins within 10 minutes of start time\n"
            "- Late: joins after grace period but before lesson ends\n"
            "- Absent: joins after lesson ends\n"
            "- Rejected: joins before lesson starts"
        ),
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Unique lesson ID.",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=AttendanceResultSerializer,
                description="Attendance marked successfully.",
            ),
            400: OpenApiResponse(description="Cannot join before lesson starts."),
            403: OpenApiResponse(description="Not enrolled in this course."),
            404: OpenApiResponse(description="Lesson not found."),
        },
    )
    @action(detail=True, methods=["post"], permission_classes=[IsStudent])
    def join(self, request: Request, pk: int = None) -> Response:
        result = services.join_lesson(lesson_id=pk, student=request.user)
        return Response(AttendanceResultSerializer(result).data)

    @extend_schema(
        tags=["Lessons"],
        summary="Get lesson attendance",
        description=(
            "**Teachers only.** Returns attendance status for all enrolled students in a lesson."
        ),
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Unique lesson ID.",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=LessonAttendanceSummarySerializer,
                description="Lesson attendance summary.",
            ),
            403: OpenApiResponse(
                description="You do not have permission to view this attendance."
            ),
            404: OpenApiResponse(description="Lesson not found."),
        },
    )
    @action(detail=True, methods=["get"], permission_classes=[IsTeacher])
    def attendance(self, request: Request, pk: int = None) -> Response:
        summary = services.get_lesson_attendance_summary(
            lesson_id=pk, teacher=request.user
        )
        return Response(LessonAttendanceSummarySerializer(summary).data)
