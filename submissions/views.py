from drf_spectacular.openapi import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.permissions import IsTeacher

from . import selectors, services
from .serializers import SubmissionCreateSerializer, SubmissionSerializer


_COURSE_PK_PARAM = OpenApiParameter(
    name="course_pk", type=OpenApiTypes.INT, location=OpenApiParameter.PATH,
    description="ID of the parent course.",
)
_ASSIGNMENT_PK_PARAM = OpenApiParameter(
    name="assignment_pk", type=OpenApiTypes.INT, location=OpenApiParameter.PATH,
    description="ID of the parent assignment.",
)
_SUBMISSION_PK_PARAM = OpenApiParameter(
    name="id", type=OpenApiTypes.INT, location=OpenApiParameter.PATH,
    description="Unique submission ID.",
)


class SubmissionViewSet(ViewSet):
    """
    Nested under /courses/{course_pk}/assignments/{assignment_pk}/submissions/
    """
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == "list":
            return [IsTeacher()]
        return [IsAuthenticated()]

    @extend_schema(
        tags=["Submissions"],
        summary="List submissions for an assignment",
        parameters=[_COURSE_PK_PARAM, _ASSIGNMENT_PK_PARAM],
        description=(
            "**Teachers only.** Returns student submissions for the specified assignment "
            "within a course the teacher owns. "
            "Each submission includes the student ID, content, status (`pending`/`graded`), "
            "and the timestamp."
        ),
        responses={
            200: SubmissionSerializer(many=True),
            403: OpenApiResponse(description="Not a teacher, or you do not own this course."),
        },
    )
    def list(self, request: Request, assignment_pk: int = None, course_pk: int = None) -> Response:
        submissions = (
            selectors.get_submissions_for_assignment(assignment_id=assignment_pk)
            .filter(assignment__course__teacher=request.user)
        )
        return Response(SubmissionSerializer(submissions, many=True).data)

    @extend_schema(
        tags=["Submissions"],
        summary="Get a specific submission",
        parameters=[_COURSE_PK_PARAM, _ASSIGNMENT_PK_PARAM, _SUBMISSION_PK_PARAM],
        description=(
            "Retrieve a single submission by its ID. "
            "Accessible to the owning student and the teacher of the submission's course."
        ),
        responses={
            200: SubmissionSerializer,
            403: OpenApiResponse(description="You do not have access to this submission."),
            404: OpenApiResponse(description="Submission not found."),
        },
    )
    def retrieve(self, request: Request, pk: int = None, assignment_pk: int = None, course_pk: int = None) -> Response:
        submission = selectors.get_submission(pk)
        is_owner = request.user == submission.student
        is_course_teacher = request.user == submission.assignment.course.teacher
        if not (is_owner or is_course_teacher):
            return Response(
                {"error": "You do not have access to this submission."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(SubmissionSerializer(submission).data)

    @extend_schema(
        tags=["Submissions"],
        summary="Submit an assignment",
        parameters=[_COURSE_PK_PARAM, _ASSIGNMENT_PK_PARAM],
        description=(
            "**Students only.** Submit work for an assignment. Rules:\n\n"
            "- The student must be enrolled in the assignment's course.\n"
            "- Only one submission is allowed per student per assignment (no re-submissions).\n"
            "- After submission, a `submission_created` notification is sent to the teacher."
        ),
        request=SubmissionCreateSerializer,
        responses={
            201: OpenApiResponse(response=SubmissionSerializer, description="Submission received."),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Not enrolled, or not a student."),
            404: OpenApiResponse(description="Assignment not found."),
            409: OpenApiResponse(description="You have already submitted this assignment."),
        },
        examples=[
            OpenApiExample(
                "Submit Assignment",
                value={"content": "The mitochondria is the powerhouse of the cell..."},
                request_only=True,
            ),
            OpenApiExample(
                "Submission Created",
                value={
                    "id": 12,
                    "assignment": 3,
                    "student": 7,
                    "content": "The mitochondria is the powerhouse of the cell...",
                    "status": "pending",
                    "submitted_at": "2026-04-10T14:30:00Z",
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    @action(detail=False, methods=["post"], url_path="submit")
    def submit(self, request: Request, assignment_pk: int = None, course_pk: int = None) -> Response:
        serializer = SubmissionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = services.submit_assignment(
            student=request.user,
            assignment_id=assignment_pk,
            content=serializer.validated_data["content"],
        )
        return Response(SubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Submissions"],
        summary="Grade a submission",
        parameters=[_COURSE_PK_PARAM, _ASSIGNMENT_PK_PARAM, _SUBMISSION_PK_PARAM],
        description=(
            "**Teachers only.** Mark a submission as graded. "
            "Only the teacher who owns the course can grade submissions."
        ),
        responses={
            200: SubmissionSerializer,
            403: OpenApiResponse(description="Not a teacher, or you do not own this course."),
            404: OpenApiResponse(description="Submission not found."),
        },
    )
    @action(detail=True, methods=["post"], url_path="grade")
    def grade(self, request: Request, pk: int = None, assignment_pk: int = None, course_pk: int = None) -> Response:
        submission = services.grade_submission(teacher=request.user, submission_id=pk)
        return Response(SubmissionSerializer(submission).data)
