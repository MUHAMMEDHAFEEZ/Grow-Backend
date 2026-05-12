from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.permissions import IsTeacher
from teachers.serializers import (
    GradeSubmissionSerializer,
    TeacherAssignmentSerializer,
    TeacherAssignmentWriteSerializer,
    TeacherSubmissionSerializer,
)
from teachers.selectors import (
    get_assignment_detail,
    get_assignment_review_summary,
    get_submissions_for_assignment,
    get_teacher_assignments,
)
from teachers.services import (
    create_teacher_assignment,
    delete_teacher_assignment,
    grade_submission,
    update_teacher_assignment,
)


@extend_schema(
    tags=["Teacher Assignments"],
    summary="List assignments",
    responses={200: TeacherAssignmentSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def list_assignments(request: Request) -> Response:
    course_id = request.query_params.get("course_id")
    assignments = get_teacher_assignments(request.user, course_id)
    return Response(TeacherAssignmentSerializer(assignments, many=True).data)


@extend_schema(
    tags=["Teacher Assignments"],
    summary="Create assignment",
    request=TeacherAssignmentWriteSerializer,
    responses={201: TeacherAssignmentSerializer},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTeacher])
def create_assignment(request: Request) -> Response:
    course_id = request.data.get("course_id")
    if not course_id:
        return Response({"error": "course_id is required."}, status=status.HTTP_400_BAD_REQUEST)
    serializer = TeacherAssignmentWriteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    assignment = create_teacher_assignment(teacher=request.user, course_id=course_id, **serializer.validated_data)
    return Response(TeacherAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Teacher Assignments"],
    summary="Get assignment detail",
    responses={200: TeacherAssignmentSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def get_assignment(request: Request, assignment_id: int) -> Response:
    assignment = get_assignment_detail(assignment_id)
    if not assignment or assignment.course.teacher_id != request.user.id:
        return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(TeacherAssignmentSerializer(assignment).data)


@extend_schema(
    tags=["Teacher Assignments"],
    summary="Update assignment",
    request=TeacherAssignmentWriteSerializer,
    responses={200: TeacherAssignmentSerializer},
)
@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated, IsTeacher])
def update_assignment(request: Request, assignment_id: int) -> Response:
    serializer = TeacherAssignmentWriteSerializer(data=request.data, partial=request.method == "PATCH")
    serializer.is_valid(raise_exception=True)
    assignment = update_teacher_assignment(
        teacher=request.user, assignment_id=assignment_id, **serializer.validated_data
    )
    return Response(TeacherAssignmentSerializer(assignment).data)


@extend_schema(
    tags=["Teacher Assignments"],
    summary="Delete assignment",
    responses={204: OpenApiResponse(description="Deleted.")},
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsTeacher])
def delete_assignment(request: Request, assignment_id: int) -> Response:
    delete_teacher_assignment(teacher=request.user, assignment_id=assignment_id)
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=["Teacher Assignments"],
    summary="Assignment review panel",
    responses={200: OpenApiResponse(description="Review summary + submissions.")},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def review_panel(request: Request, assignment_id: int) -> Response:
    assignment = get_assignment_detail(assignment_id)
    if not assignment or assignment.course.teacher_id != request.user.id:
        return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    summary = get_assignment_review_summary(assignment)
    submissions = get_submissions_for_assignment(assignment_id)
    return Response({
        "summary": summary,
        "submissions": TeacherSubmissionSerializer(submissions, many=True).data,
    })


@extend_schema(
    tags=["Teacher Assignments"],
    summary="Grade a submission",
    request=GradeSubmissionSerializer,
    responses={200: TeacherSubmissionSerializer},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTeacher])
def grade_submission_view(request: Request, submission_id: int) -> Response:
    serializer = GradeSubmissionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    submission = grade_submission(
        teacher=request.user,
        submission_id=submission_id,
        raw_score=float(serializer.validated_data["raw_score"]),
        feedback=serializer.validated_data.get("feedback", ""),
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    return Response(TeacherSubmissionSerializer(submission).data)
