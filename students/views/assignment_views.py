from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from assignments.models import Assignment
from core.permissions import IsStudent
from students.selectors import get_assignment_detail
from students.serializers.assignment_serializers import (
    AssignmentDetailSerializer,
    AssignmentSubmitSerializer,
)
from students.services.file_validation_service import validate_upload
from submissions.models import Submission


@extend_schema(
    tags=["Student Assignments"],
    summary="Assignment detail",
    description="Get assignment details with submission status.",
    responses={200: AssignmentDetailSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStudent])
def assignment_detail_view(request, assignment_id):
    try:
        data = get_assignment_detail(assignment_id, request.user)
        serializer = AssignmentDetailSerializer(data)
        return Response(serializer.data)
    except Assignment.DoesNotExist:
        return Response({"error": "Assignment not found"}, status=404)


@extend_schema(
    tags=["Student Assignments"],
    summary="Submit assignment",
    description="Upload a file as assignment submission.",
    request=AssignmentSubmitSerializer,
    responses={200: dict},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def assignment_submit_view(request, assignment_id):
    try:
        assignment = Assignment.objects.get(id=assignment_id)
    except Assignment.DoesNotExist:
        return Response({"error": "Assignment not found"}, status=404)

    serializer = AssignmentSubmitSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    file = serializer.validated_data["file"]
    is_valid, error = validate_upload(file)
    if not is_valid:
        return Response({"error": error}, status=400)

    submission, created = Submission.objects.update_or_create(
        assignment=assignment,
        student=request.user,
        defaults={
            "file": file,
            "status": Submission.Status.PENDING,
        },
    )

    return Response({"message": "Assignment submitted successfully", "file": submission.file.name})
