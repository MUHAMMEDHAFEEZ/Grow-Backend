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

from assignments.views import AssignmentViewSet  # noqa: F401 - re-exported for api_urls
from core.permissions import IsStudent, IsTeacher
from submissions.views import SubmissionViewSet  # noqa: F401 - re-exported for api_urls

from . import selectors, services
from .models import Course, Quiz as QuizModel
from .serializers import (
    AttendanceResultSerializer,
    CourseProgressSerializer,
    CourseSerializer,
    CourseWriteSerializer,
    LessonActivitySerializer,
    LessonAttendanceSummarySerializer,
    LessonSerializer,
    LessonTrackSerializer,
    QuizAttemptSerializer,
    QuizSerializer,
    QuizSubmitSerializer,
    StudentCourseSerializer,
)


_COURSE_PK_PARAM = OpenApiParameter(
    name="id",
    type=OpenApiTypes.INT,
    location=OpenApiParameter.PATH,
    description="Unique course ID.",
)


class CourseViewSet(viewsets.ViewSet):
    serializer_class = CourseSerializer
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
            "**Students only.** Lazy enrollment — creates an engagement record "
            "on first interaction. Returns existing record if already enrolled."
        ),
        request=None,
        responses={
            201: OpenApiResponse(
                response=StudentCourseSerializer, description="Enrolled successfully."
            ),
            403: OpenApiResponse(description="Only students can enroll."),
            404: OpenApiResponse(description="Course not found."),
        },
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def enroll(self, request: Request, pk: int = None) -> Response:
        enrollment = services.enroll_student(course_id=pk, student=request.user)
        serializer = StudentCourseSerializer(enrollment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Courses"],
        summary="List enrolled students",
        parameters=[_COURSE_PK_PARAM],
        description="**Teachers only.** Returns all students engaged in this course.",
        responses={200: StudentCourseSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], permission_classes=[IsTeacher])
    def students(self, request: Request, pk: int = None) -> Response:
        enrollments = selectors.get_course_students(course_id=pk)
        return Response(StudentCourseSerializer(enrollments, many=True).data)

    @extend_schema(
        tags=["Courses"],
        summary="Set course grade",
        parameters=[_COURSE_PK_PARAM],
        description="**Teachers only.** Assign a grade level to this course.",
        request=None,
        responses={
            200: CourseSerializer,
            403: OpenApiResponse(description="You do not own this course."),
            404: OpenApiResponse(description="Course or grade not found."),
        },
    )
    @action(detail=True, methods=["post"], permission_classes=[IsTeacher])
    def set_grade(self, request: Request, pk: int = None) -> Response:
        grade_id = request.data.get("grade_id")
        if not grade_id:
            return Response(
                {"error": "grade_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        course = services.set_course_grade(
            course_id=pk, teacher=request.user, grade_id=grade_id
        )
        return Response(CourseSerializer(course).data)

    @extend_schema(
        tags=["Courses"],
        summary="Course progress (teacher)",
        parameters=[_COURSE_PK_PARAM],
        description="**Teachers only.** Returns progress for all engaged students.",
        responses={200: CourseProgressSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], permission_classes=[IsTeacher])
    def progress(self, request: Request, pk: int = None) -> Response:
        try:
            course = selectors.get_all_courses().get(pk=pk)
        except Course.DoesNotExist:
            return Response(
                {"error": "Not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if course.teacher_id != request.user.pk:
            return Response(
                {"error": "You do not own this course."},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = selectors.get_all_progress_for_course(course)
        return Response(CourseProgressSerializer(qs, many=True).data)

    @extend_schema(
        tags=["Courses"],
        summary="My course progress (student)",
        parameters=[_COURSE_PK_PARAM],
        description="**Students only.** Returns the authenticated student's progress.",
        responses={200: CourseProgressSerializer},
    )
    @action(
        detail=True, methods=["get"], permission_classes=[IsAuthenticated]
    )
    def progress_me(self, request: Request, pk: int = None) -> Response:
        if not request.user.is_student:
            return Response(
                {"error": "Only students can view their progress."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            course = selectors.get_all_courses().get(pk=pk)
        except Course.DoesNotExist:
            return Response(
                {"error": "Not found."}, status=status.HTTP_404_NOT_FOUND
            )
        progress = selectors.get_course_progress(request.user, course)
        if not progress:
            return Response(
                {
                    "progress_percentage": 0,
                    "study_time_seconds": 0,
                    "study_time_formatted": "0m",
                    "last_activity": None,
                    "completion_status": "not_started",
                }
            )
        return Response(CourseProgressSerializer(progress).data)

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


class QuizViewSet(viewsets.ViewSet):
    """
    ViewSet for quiz operations.
    Routes: /quizzes/{id}/attempt/, /quizzes/{id}/attempts/
    """
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Quizzes"],
        summary="Submit a quiz attempt",
        description="**Students only.** Submit a score for a quiz. Attempt number auto-increments.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Unique quiz ID.",
            ),
        ],
        request=QuizSubmitSerializer,
        responses={
            201: QuizAttemptSerializer,
            403: OpenApiResponse(description="Permission denied."),
            404: OpenApiResponse(description="Quiz not found."),
            429: OpenApiResponse(description="Rate limit exceeded."),
        },
    )
    @action(detail=True, methods=["post"], permission_classes=[IsStudent])
    def attempt(self, request: Request, pk: int = None) -> Response:
        serializer = QuizSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = services.submit_quiz_attempt(
            student=request.user,
            quiz_id=pk,
            score=serializer.validated_data["score"],
        )
        return Response(QuizAttemptSerializer(attempt).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Quizzes"],
        summary="List quiz attempts",
        description="**Student:** own attempts. **Teacher:** all attempts for their quiz.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Unique quiz ID.",
            ),
        ],
        responses={200: QuizAttemptSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def attempts(self, request: Request, pk: int = None) -> Response:
        from .selectors import get_quiz_attempts, get_quiz_attempts_for_teacher
        try:
            quiz = QuizModel.objects.get(pk=pk)
        except QuizModel.DoesNotExist:
            return Response(
                {"error": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if request.user.is_student:
            qs = get_quiz_attempts(request.user, quiz)
        elif request.user.is_teacher:
            qs = get_quiz_attempts_for_teacher(quiz)
        else:
            return Response(
                {"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )
        return Response(QuizAttemptSerializer(qs, many=True).data)

    @extend_schema(
        tags=["Quizzes"],
        summary="Get quiz details",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Unique quiz ID.",
            ),
        ],
        responses={200: QuizSerializer},
    )
    def retrieve(self, request: Request, pk: int = None) -> Response:
        try:
            quiz = QuizModel.objects.get(pk=pk)
        except QuizModel.DoesNotExist:
            return Response(
                {"error": "Not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(QuizSerializer(quiz, context={"request": request}).data)

    @extend_schema(
        tags=["Quizzes"],
        summary="Create a quiz",
        description="**Teachers only.** Create a quiz for a course you own.",
        request=QuizSerializer,
        responses={
            201: QuizSerializer,
            403: OpenApiResponse(description="Permission denied."),
        },
    )
    def create(self, request: Request) -> Response:
        serializer = QuizSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quiz = services.create_quiz(
            teacher=request.user,
            course_id=serializer.validated_data["course_id"],
            title=serializer.validated_data["title"],
            max_score=serializer.validated_data["max_score"],
            lesson_id=serializer.validated_data.get("lesson_id"),
        )
        return Response(QuizSerializer(quiz, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Quizzes"],
        summary="List quizzes",
        parameters=[
            OpenApiParameter(
                name="course", type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by course ID.",
            ),
        ],
        responses={200: QuizSerializer(many=True)},
    )
    def list(self, request: Request) -> Response:
        qs = QuizModel.objects.select_related("course").all()
        course_id = request.query_params.get("course")
        if course_id:
            qs = qs.filter(course_id=course_id)
        return Response(QuizSerializer(qs, many=True, context={"request": request}).data)


class LessonActivityViewSet(viewsets.ViewSet):
    """
    ViewSet for lesson activity tracking.
    Routes: /lessons/{id}/track/, /lessons/{id}/complete/
    """
    serializer_class = LessonActivitySerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Lessons"],
        summary="Track lesson watch time",
        description="**Students only.** Increment watch duration for a lesson.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Unique lesson ID.",
            ),
        ],
        request=LessonTrackSerializer,
        responses={200: LessonActivitySerializer},
    )
    @action(detail=True, methods=["post"], permission_classes=[IsStudent])
    def track(self, request: Request, pk: int = None) -> Response:
        serializer = LessonTrackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activity = services.track_lesson_watch(
            student=request.user,
            lesson_id=pk,
            watch_duration_seconds=serializer.validated_data.get(
                "watch_duration_seconds", 0
            ),
        )
        return Response(LessonActivitySerializer(activity).data)

    @extend_schema(
        tags=["Lessons"],
        summary="Complete a lesson",
        description="**Students only.** Mark a lesson as completed and update course progress.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Unique lesson ID.",
            ),
        ],
        responses={200: LessonActivitySerializer},
    )
    @action(detail=True, methods=["post"], permission_classes=[IsStudent])
    def complete(self, request: Request, pk: int = None) -> Response:
        activity = services.complete_lesson(
            student=request.user,
            lesson_id=pk,
        )
        return Response(LessonActivitySerializer(activity).data)


class LessonViewSet(viewsets.ViewSet):
    """
    ViewSet for lesson-specific actions that operate directly on lesson ID.
    Routes: /lessons/{id}/join/, /lessons/{id}/attendance/
    """

    serializer_class = LessonSerializer
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
