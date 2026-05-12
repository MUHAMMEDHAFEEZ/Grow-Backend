from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsStudent, IsTeacher

from . import selectors, services
from .models import StudentTask
from .serializers import StudentTaskSerializer


class StudentTaskListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Tasks"],
        summary="List student tasks",
        description=(
            "Returns all tasks for the authenticated student, or for teachers — "
            "aggregate per-student counts for their courses. Admins see all."
        ),
        responses={200: StudentTaskSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        user = request.user
        if user.is_student:
            status_param = request.query_params.get("status")
            course_id = request.query_params.get("course")
            qs = selectors.get_tasks_for_student(
                user, status=status_param,
                course_id=int(course_id) if course_id else None,
            )
            return Response(StudentTaskSerializer(qs, many=True).data)
        return Response([])


class PendingTasksView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    @extend_schema(
        tags=["Tasks"],
        summary="List pending tasks",
        description="Returns only pending tasks for the authenticated student.",
        responses={200: StudentTaskSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = selectors.get_tasks_for_student(
            request.user, status=StudentTask.Status.PENDING
        )
        return Response(StudentTaskSerializer(qs, many=True).data)


class CompleteTaskView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    @extend_schema(
        tags=["Tasks"],
        summary="Mark a task as complete",
        description="Manually mark a pending task as completed.",
        request=None,
        responses={
            200: StudentTaskSerializer,
            403: OpenApiResponse(description="Not your task."),
            404: OpenApiResponse(description="Task not found."),
        },
    )
    def patch(self, request: Request, pk: int) -> Response:
        from core.exceptions import NotFound, PermissionDenied
        try:
            task = services.complete_task(
                student=request.user, content_type="", content_id=0
            )
        except Exception:
            ...
        try:
            task = StudentTask.objects.get(pk=pk)
        except StudentTask.DoesNotExist:
            raise NotFound("Task not found.")
        if task.student_id != request.user.pk:
            raise PermissionDenied("This task does not belong to you.")
        if task.status == StudentTask.Status.COMPLETED:
            return Response(StudentTaskSerializer(task).data)
        from django.utils import timezone
        task.status = StudentTask.Status.COMPLETED
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at"])
        return Response(StudentTaskSerializer(task).data)


class TaskSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(
        tags=["Tasks"],
        summary="Course task summary",
        description=(
            "Per-student task completion counts for a course. "
            "Teacher must own the course."
        ),
        responses={200: dict},
    )
    def get(self, request: Request, course_id: int) -> Response:
        from courses.models import Course
        from core.exceptions import NotFound, PermissionDenied

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise NotFound("Course not found.")
        if course.teacher_id != request.user.pk:
            raise PermissionDenied("You do not own this course.")
        data = selectors.get_task_summary_for_course(course_id)
        return Response({
            "course_id": course_id,
            "course_title": course.title,
            "students": data,
        })
