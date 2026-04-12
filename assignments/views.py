from drf_spectacular.openapi import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.permissions import IsTeacher

from . import selectors, services
from .serializers import AssignmentSerializer, AssignmentWriteSerializer


_COURSE_PK_PARAM = OpenApiParameter(
    name="course_pk", type=OpenApiTypes.INT, location=OpenApiParameter.PATH,
    description="ID of the parent course.",
)
_ASSIGNMENT_PK_PARAM = OpenApiParameter(
    name="id", type=OpenApiTypes.INT, location=OpenApiParameter.PATH,
    description="Unique assignment ID.",
)


class AssignmentViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Assignments"],
        summary="List assignments for a course",
        parameters=[_COURSE_PK_PARAM],
        description=(
            "Returns all assignments for the given course. "
            "Accessible to all enrolled students and the course teacher. "
            "Results are ordered by `due_date` ascending."
        ),
        responses={200: AssignmentSerializer(many=True)},
    )
    def list(self, request: Request, course_pk: int = None) -> Response:
        assignments = selectors.get_assignments_for_course(course_id=course_pk)
        return Response(AssignmentSerializer(assignments, many=True).data)

    @extend_schema(
        tags=["Assignments"],
        summary="Get assignment details",
        parameters=[_COURSE_PK_PARAM, _ASSIGNMENT_PK_PARAM],
        description="Retrieve full details for a single assignment.",
        responses={
            200: AssignmentSerializer,
            404: OpenApiResponse(description="Assignment not found."),
        },
    )
    def retrieve(self, request: Request, pk: int = None, course_pk: int = None) -> Response:
        assignment = selectors.get_assignment(pk)
        return Response(AssignmentSerializer(assignment).data)

    @extend_schema(
        tags=["Assignments"],
        summary="Create an assignment",
        parameters=[_COURSE_PK_PARAM],
        description=(
            "**Teachers only.** Creates a new assignment under the specified course. "
            "Once created, an `assignment_created` event is emitted and enrolled students "
            "receive an in-app notification."
        ),
        request=AssignmentWriteSerializer,
        responses={
            201: OpenApiResponse(response=AssignmentSerializer, description="Assignment created."),
            400: OpenApiResponse(description="Validation error (e.g. missing due_date)."),
            403: OpenApiResponse(description="Only teachers can create assignments."),
            404: OpenApiResponse(description="Course not found or you do not own it."),
        },
        examples=[
            OpenApiExample(
                "Create Assignment",
                value={
                    "title": "Math Quiz — Chapter 3",
                    "description": "Cover pages 45-60. Show all working.",
                    "due_date": "2026-05-20T23:59:00Z",
                },
                request_only=True,
            ),
        ],
    )
    def create(self, request: Request, course_pk: int = None) -> Response:
        serializer = AssignmentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = services.create_assignment(
            teacher=request.user, course_id=course_pk, **serializer.validated_data
        )
        return Response(AssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Assignments"],
        summary="Update an assignment",
        parameters=[_COURSE_PK_PARAM, _ASSIGNMENT_PK_PARAM],
        description="**Teachers only.** Partially or fully update an assignment you own.",
        request=AssignmentWriteSerializer,
        responses={
            200: AssignmentSerializer,
            403: OpenApiResponse(description="You do not own this assignment's course."),
            404: OpenApiResponse(description="Assignment not found."),
        },
    )
    def update(self, request: Request, pk: int = None, course_pk: int = None) -> Response:
        serializer = AssignmentWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        assignment = services.update_assignment(
            assignment_id=pk, teacher=request.user, **serializer.validated_data
        )
        return Response(AssignmentSerializer(assignment).data)

    @extend_schema(
        tags=["Assignments"],
        summary="Delete an assignment",
        parameters=[_COURSE_PK_PARAM, _ASSIGNMENT_PK_PARAM],
        description="**Teachers only.** Permanently deletes an assignment and all its submissions.",
        responses={
            204: OpenApiResponse(description="Deleted successfully."),
            403: OpenApiResponse(description="You do not own this assignment's course."),
            404: OpenApiResponse(description="Assignment not found."),
        },
    )
    def destroy(self, request: Request, pk: int = None, course_pk: int = None) -> Response:
        services.delete_assignment(assignment_id=pk, teacher=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
