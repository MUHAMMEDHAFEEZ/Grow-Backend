from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.selectors import get_child_for_parent
from . import selectors, services
from .serializers import AttendanceRecordSerializer, MarkAttendanceSerializer


class AttendanceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Attendance"],
        summary="List attendance records",
        description=(
            "Query attendance records. Behaviour depends on role and query params:\n\n"
            "| Caller | Result |\n"
            "|---|---|\n"
            "| Teacher with `?course=<id>` | All records for that course |\n"
            "| Teacher with `?course=<id>&date=YYYY-MM-DD` | Records for one day |\n"
            "| Any with `?student=<id>` | Records for a specific student |\n"
            "| Student (no params) | Own attendance history |\n"
            "| Parent (no params) | Linked child's attendance history |"
        ),
        parameters=[
            OpenApiParameter(
                name="course",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by course ID.",
                required=False,
            ),
            OpenApiParameter(
                name="student",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by student ID.",
                required=False,
            ),
            OpenApiParameter(
                name="date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by date (YYYY-MM-DD, e.g. 2026-04-10). Only applies when `course` is also provided.",
                required=False,
            ),
        ],
        responses={200: AttendanceRecordSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        course_id = request.query_params.get("course")
        student_id = request.query_params.get("student")
        date = request.query_params.get("date")

        if course_id:
            records = selectors.get_attendance_for_course(course_id=int(course_id), date=date)
        elif student_id:
            records = selectors.get_attendance_for_student(student_id=int(student_id))
        elif request.user.is_student:
            records = selectors.get_attendance_for_student(request.user.pk)
        elif request.user.is_parent:
            child = get_child_for_parent(request.user)
            records = selectors.get_attendance_for_student(child.pk) if child else []
        else:
            records = []

        return Response(AttendanceRecordSerializer(records, many=True).data)

    @extend_schema(
        tags=["Attendance"],
        summary="Mark attendance for a session",
        description=(
            "**Teachers only.** Record attendance for an entire class session in one call.\n\n"
            "- Each `records` entry specifies one student and their status.\n"
            "- Calling this endpoint again for the same `(course, student, date)` will **update** "
            "  the existing record (upsert behaviour).\n"
            "- When a student is marked `absent`, their linked parent receives an in-app notification."
        ),
        request=MarkAttendanceSerializer,
        responses={
            201: OpenApiResponse(
                response=AttendanceRecordSerializer(many=True),
                description="Attendance records saved.",
            ),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Only teachers can mark attendance."),
            404: OpenApiResponse(description="Course not found or you do not own it."),
        },
        examples=[
            OpenApiExample(
                "Mark Attendance",
                value={
                    "course": 1,
                    "date": "2026-04-10",
                    "records": [
                        {"student_id": 5, "status": "present"},
                        {"student_id": 6, "status": "absent"},
                        {"student_id": 7, "status": "late"},
                    ],
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request: Request) -> Response:
        serializer = MarkAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        records = services.mark_attendance(
            teacher=request.user,
            course_id=d["course"],
            date=d["date"],
            records=d["records"],
        )
        return Response(AttendanceRecordSerializer(records, many=True).data, status=status.HTTP_201_CREATED)
