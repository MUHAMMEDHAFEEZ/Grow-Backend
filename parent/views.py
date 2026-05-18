from django.http import HttpResponse
from django.utils import timezone

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from notifications.models import Notification
from notifications.serializers import NotificationSerializer
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import Conflict, RateLimitExceeded, ValidationError
from core.permissions import IsParent

from students.models import Student
from students.services.linking_service import link_student_by_id

from . import services
from .selectors import verify_parent_owns_student
from .serializers import (
    AnalyticsSerializer,
    AttendanceSerializer,
    DashboardSerializer,
    ParentLinkSerializer,
    ParentNotificationSerializer,
    ReportSerializer,
    SettingsSerializer,
    StudentListSerializer,
)
from .services.attendance_service import (
    get_activity_calendar,
    get_attendance_rate,
    get_study_streak,
    get_total_study_hours,
)
from .services.gpa_service import get_cumulative_gpa, get_monthly_gpas
from .services.report_service import (
    generate_pdf_report,
    get_monthly_report,
)
from .services.schedule_service import get_upcoming_schedule
from .services.xp_service import get_monthly_xp, get_total_xp


class DashboardView(APIView):
    permission_classes = [IsAuthenticated, IsParent]

    @extend_schema(
        tags=["Parent"],
        summary="Get parent dashboard",
        description=(
            "Returns analytics dashboard for the specified student. "
            "Only the parent of the student can view this dashboard."
        ),
        parameters=[
            OpenApiParameter(
                name="student_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the student to view dashboard for.",
                required=True,
            ),
        ],
        responses={200: DashboardSerializer},
    )
    def get(self, request: Request, student_id: int) -> Response:
        if not verify_parent_owns_student(request.user, student_id):
            return Response(
                {"error": "You can only view your child's dashboard."},
                status=403,
            )

        dashboard = services.get_parent_dashboard(
            parent=request.user,
            student_id=student_id,
        )
        gpa = get_cumulative_gpa(student_id)
        xp = get_total_xp(student_id)
        upcoming = get_upcoming_schedule(student_id)

        result = {
            "gpa": gpa,
            "study_hours": dashboard["study_hours"],
            "xp": xp,
            "engagement": dashboard["engagement"],
            "subject_performance": dashboard["subjects"],
            "upcoming_schedule": upcoming,
            "recent_activity": dashboard["recent_activity"],
        }
        return Response(DashboardSerializer(result).data)


# ── Students List ───────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Parent"],
    summary="List linked students",
    description="Returns all students linked to the authenticated parent.",
    responses={200: StudentListSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsParent])
def list_students(request: Request) -> Response:
    students = Student.objects.filter(parent=request.user).select_related(
        "grade", "school"
    )
    return Response(StudentListSerializer(students, many=True).data)


# ── Add Student ─────────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Parent"],
    summary="Link student with student ID",
    description=(
        "Links an existing student to the authenticated parent using "
        "school, full name, student ID, and grade verification."
    ),
    request=ParentLinkSerializer,
    responses={
        200: {"description": "Student linked successfully."},
        400: {"description": "Information does not match any student."},
        409: {"description": "Student already linked to another parent."},
        429: {"description": "Too many failed attempts. Rate limited."},
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsParent])
def add_student(request: Request) -> Response:
    serializer = ParentLinkSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    try:
        student = link_student_by_id(
            parent=request.user,
            school_id=serializer.validated_data["school_id"],
            full_name=serializer.validated_data["full_name"],
            student_id=serializer.validated_data["student_id"],
            grade_id=serializer.validated_data["grade_id"],
        )
    except RateLimitExceeded as exc:
        return Response({"error": exc.detail}, status=429)
    except Conflict as exc:
        return Response({"error": exc.detail}, status=409)
    except ValidationError as exc:
        return Response({"error": str(exc.detail)}, status=400)

    return Response({
        "message": "Student linked successfully",
        "student_id": student.student_id,
        "full_name": student.full_name,
    }, status=200)


# ── Analytics ───────────────────────────────────────────────────────────────────

VALID_FILTERS = {"weekly", "monthly", "yearly"}


@extend_schema(
    tags=["Parent"],
    summary="Get student analytics",
    description=(
        "Returns performance trends for the specified student. "
        "Accepts `filter` query param: weekly, monthly, or yearly."
    ),
    parameters=[
        OpenApiParameter(
            name="student_id",
            type=int,
            location=OpenApiParameter.PATH,
            required=True,
        ),
        OpenApiParameter(
            name="filter",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Aggregation period: weekly, monthly, or yearly.",
        ),
    ],
    responses={200: AnalyticsSerializer, 400: {"description": "Invalid filter value."}},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsParent])
def analytics(request: Request, student_id: int) -> Response:
    if not verify_parent_owns_student(request.user, student_id):
        return Response({"error": "You can only view your child's analytics."}, status=403)

    period = request.query_params.get("filter", "monthly")
    if period not in VALID_FILTERS:
        return Response(
            {"error": f"Invalid filter '{period}'. Must be one of: weekly, monthly, yearly."},
            status=400,
        )

    now = timezone.now()
    year = now.year

    monthly_gpas = get_monthly_gpas(student_id, year)
    overall_academic_trend = [
        {"period": f"Month {m['month']}", "average": m["average"]}
        for m in monthly_gpas
    ]

    dashboard = services._compute_dashboard(student_id)
    study_hours_data = []
    for month in range(1, now.month + 1):
        xp_data = get_monthly_xp(student_id, year, month)
        study_hours_data.append({
            "period": f"Month {month}",
            "hours": xp_data["total"] / 10.0,
        })

    return Response(AnalyticsSerializer({
        "overall_academic_trend": overall_academic_trend,
        "study_hours": study_hours_data,
        "subject_breakdown": [
            {"name": s["name"], "average": s["average"], "grade": s["grade"]}
            for s in dashboard["subjects"]
        ],
    }).data)


# ── Attendance ──────────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Parent"],
    summary="Get student attendance",
    description=(
        "Returns attendance data including study hours, streak, "
        "attendance rate, and monthly activity calendar."
    ),
    parameters=[
        OpenApiParameter(
            name="student_id",
            type=int,
            location=OpenApiParameter.PATH,
            required=True,
        ),
    ],
    responses={200: AttendanceSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsParent])
def attendance(request: Request, student_id: int) -> Response:
    if not verify_parent_owns_student(request.user, student_id):
        return Response({"error": "You can only view your child's attendance."}, status=403)

    now = timezone.now()

    return Response(AttendanceSerializer({
        "total_study_hours": get_total_study_hours(student_id),
        "study_streak": get_study_streak(student_id),
        "attendance_rate": get_attendance_rate(student_id, now.year, now.month),
        "activity_calendar": get_activity_calendar(student_id, now.year, now.month),
    }).data)


# ── Report ──────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Parent"],
    summary="Get monthly report",
    description="Returns a monthly performance report for the specified student.",
    parameters=[
        OpenApiParameter(
            name="student_id",
            type=int,
            location=OpenApiParameter.PATH,
            required=True,
        ),
        OpenApiParameter(
            name="month",
            type=str,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Month in YYYY-MM format.",
        ),
    ],
    responses={200: ReportSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsParent])
def report(request: Request, student_id: int) -> Response:
    if not verify_parent_owns_student(request.user, student_id):
        return Response({"error": "You can only view your child's report."}, status=403)

    month = request.query_params.get("month", "")
    if not month:
        return Response({"error": "month query param is required (YYYY-MM)."}, status=400)

    try:
        data = get_monthly_report(student_id, month)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)

    return Response(ReportSerializer(data).data)


@extend_schema(
    tags=["Parent"],
    summary="Print monthly report as PDF",
    description="Returns a PDF version of the monthly report.",
    parameters=[
        OpenApiParameter(
            name="student_id",
            type=int,
            location=OpenApiParameter.PATH,
            required=True,
        ),
        OpenApiParameter(
            name="month",
            type=str,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Month in YYYY-MM format.",
        ),
    ],
    responses={200: {"description": "PDF file."}},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsParent])
def report_print(request: Request, student_id: int) -> Response:
    if not verify_parent_owns_student(request.user, student_id):
        return Response({"error": "You can only view your child's report."}, status=403)

    month = request.query_params.get("month", "")
    if not month:
        return Response({"error": "month query param is required (YYYY-MM)."}, status=400)

    pdf = generate_pdf_report(student_id, month)
    if pdf is None:
        return Response({"error": "Failed to generate PDF."}, status=500)

    return HttpResponse(pdf, content_type="application/pdf")


# ── Notifications ───────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Parent"],
    summary="List parent notifications",
    description="Returns a paginated list of notifications for the authenticated parent.",
    parameters=[
        OpenApiParameter(
            name="page",
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Page number.",
        ),
    ],
    responses={200: ParentNotificationSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsParent])
def notifications_list(request: Request) -> Response:
    qs = Notification.objects.filter(parent=request.user).order_by("-created_at")

    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))
    start = (page - 1) * page_size
    end = start + page_size

    total = qs.count()
    results = qs[start:end]

    return Response({
        "count": total,
        "next": f"?page={page + 1}&page_size={page_size}" if end < total else None,
        "previous": f"?page={page - 1}&page_size={page_size}" if page > 1 else None,
        "results": ParentNotificationSerializer(results, many=True).data,
    })


@extend_schema(
    tags=["Parent"],
    summary="Mark notification as read",
    description="Marks a single notification as read. Only the notification owner can do this.",
    request=None,
    parameters=[
        OpenApiParameter(
            name="id",
            type=int,
            location=OpenApiParameter.PATH,
            required=True,
        ),
    ],
    responses={200: OpenApiResponse(response=NotificationSerializer, description="Notification marked as read.")},
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsParent])
def notification_read(request: Request, notification_id: int) -> Response:
    try:
        notif = Notification.objects.get(pk=notification_id, parent=request.user)
    except Notification.DoesNotExist:
        return Response({"error": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)

    notif.is_read = True
    notif.save(update_fields=["is_read"])
    return Response({"status": "ok"})


# ── Settings ────────────────────────────────────────────────────────────────────

class SettingsView(APIView):
    permission_classes = [IsAuthenticated, IsParent]

    @extend_schema(
        tags=["Parent"],
        summary="Get settings",
        description="Returns profile, linked students, and notification preference.",
        responses={200: SettingsSerializer},
    )
    def get(self, request: Request) -> Response:
        students = Student.objects.filter(parent=request.user).select_related(
            "grade", "school"
        )
        data = {
            "user": request.user,
            "linked_students": students,
        }
        return Response(SettingsSerializer(data).data)

    @extend_schema(
        tags=["Parent"],
        summary="Update settings",
        description="Partially updates profile (full_name, notifications_enabled).",
        request=SettingsSerializer,
        responses={200: SettingsSerializer},
    )
    def patch(self, request: Request) -> Response:
        user = request.user
        full_name = request.data.get("full_name")
        notifications_enabled = request.data.get("notifications_enabled")

        if full_name is not None:
            parts = full_name.split()
            if parts:
                user.first_name = parts[0]
                user.last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        if notifications_enabled is not None:
            user.notifications_enabled = bool(notifications_enabled)

        update_fields = []
        if full_name is not None:
            update_fields.extend(["first_name", "last_name"])
        if notifications_enabled is not None:
            update_fields.append("notifications_enabled")
        if update_fields:
            user.save(update_fields=update_fields)

        students = Student.objects.filter(parent=request.user).select_related(
            "grade", "school"
        )
        data = {
            "user": request.user,
            "linked_students": students,
        }
        return Response(SettingsSerializer(data).data)