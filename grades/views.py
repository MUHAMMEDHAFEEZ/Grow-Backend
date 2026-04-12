from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.selectors import get_child_for_parent
from core.permissions import IsTeacher
from . import selectors, services
from .serializers import GradeSerializer, GradeWriteSerializer


class GradeSubmissionView(APIView):
    """POST /submissions/{submission_pk}/grade/"""
    permission_classes = [IsTeacher]

    @extend_schema(
        tags=["Grades"],
        summary="Grade a submission",
        description=(
            "**Teachers only.** Assign a numeric score and optional feedback to a student submission.\n\n"
            "**Rules:**\n"
            "- The submission must belong to a course the teacher owns.\n"
            "- A submission can only be graded once (raises `409` if already graded).\n\n"
            "**Side effects on success:**\n"
            "- Submission `status` changes to `graded`.\n"
            "- `submission_graded` event is emitted.\n"
            "- Student receives an in-app notification.\n"
            "- Any linked parent also receives a notification."
        ),
        request=GradeWriteSerializer,
        responses={
            200: OpenApiResponse(response=GradeSerializer, description="Grade assigned successfully."),
            400: OpenApiResponse(description="Validation error (e.g. score out of range)."),
            403: OpenApiResponse(description="You do not own this submission's course."),
            404: OpenApiResponse(description="Submission not found."),
            409: OpenApiResponse(description="This submission is already graded."),
        },
        examples=[
            OpenApiExample(
                "Grade Submission",
                value={"score": 87.5, "feedback": "Good analysis, but the conclusion needs more detail."},
                request_only=True,
            ),
            OpenApiExample(
                "Grade Response",
                value={
                    "id": 5,
                    "submission": 12,
                    "score": "87.50",
                    "feedback": "Good analysis, but the conclusion needs more detail.",
                    "graded_by": 2,
                    "graded_at": "2026-04-10T15:00:00Z",
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request: Request, submission_pk: int) -> Response:
        serializer = GradeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        grade = services.grade_submission(
            teacher=request.user,
            submission_id=submission_pk,
            **serializer.validated_data,
        )
        return Response(GradeSerializer(grade).data, status=status.HTTP_200_OK)


class GradeListView(APIView):
    """GET /grades/?student=<id>&course=<id>"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Grades"],
        summary="List grades",
        description=(
            "Query grades based on the caller's role:\n\n"
            "| Role | Behavior |\n"
            "|---|---|\n"
            "| **Student** | Returns own grades (query params ignored) |\n"
            "| **Teacher** | Use `?student=<id>` or `?course=<id>` to filter |\n"
            "| **Parent** | Returns their linked child's grades |\n\n"
            "Results include score, feedback, and the grading timestamp."
        ),
        parameters=[
            OpenApiParameter(
                name="student",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter grades by student ID. (Teacher use only)",
                required=False,
            ),
            OpenApiParameter(
                name="course",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter grades by course ID. (Teacher use only)",
                required=False,
            ),
        ],
        responses={200: GradeSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        student_id = request.query_params.get("student")
        course_id = request.query_params.get("course")
        user = request.user

        if user.is_student:
            grades = selectors.get_grades_for_student(user.pk)
        elif student_id:
            grades = selectors.get_grades_for_student(int(student_id))
        elif course_id:
            grades = selectors.get_grades_for_course(int(course_id))
        elif user.is_parent:
            child = get_child_for_parent(user)
            grades = selectors.get_grades_for_student(child.pk) if child else []
        else:
            grades = []

        return Response(GradeSerializer(grades, many=True).data)
