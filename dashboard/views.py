"""
dashboard/views.py — API endpoints for the dashboard.

No business logic here — delegates to selectors.py and services.py.
"""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .permissions import IsSchoolAdmin, IsTeacherOrSchoolAdmin
from .selectors import (
    get_class_detail,
    get_classes_list,
    get_dashboard_overview,
    get_report_summary,
    get_risk_summary,
    get_student_profile,
)
from .serializers import (
    ClassCardSerializer,
    ClassDetailSerializer,
    DashboardInsightSerializer,
    DashboardOverviewSerializer,
    ReportSummarySerializer,
    RiskSummarySerializer,
    StudentNoteCreateSerializer,
    StudentNoteSerializer,
    StudentProfileSerializer,
)
from .services import (
    add_student_note,
    dismiss_insight,
    generate_report_excel,
    generate_report_pdf,
)


@extend_schema(
    tags=["Dashboard"],
    summary="Get dashboard overview",
    description="Returns KPIs, active alerts, and chart data for the dashboard overview page.",
    responses={200: DashboardOverviewSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacherOrSchoolAdmin])
def dashboard_overview(request):
    period = request.query_params.get("period", "month")
    academic_year = request.query_params.get("academic_year")
    data = get_dashboard_overview(period=period, academic_year=academic_year)
    return Response(data)


@extend_schema(
    tags=["Dashboard"],
    summary="List classes",
    description="Returns paginated list of classes with health metrics.",
    responses={200: ClassCardSerializer(many=True)},
    operation_id="dashboard_classes_list",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacherOrSchoolAdmin])
def classes_list(request):
    teacher_id = request.query_params.get("teacher_id")
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))
    if teacher_id:
        teacher_id = int(teacher_id)
    data = get_classes_list(teacher_id=teacher_id, page=page, page_size=page_size)
    return Response(data)


@extend_schema(
    tags=["Dashboard"],
    summary="Get class detail",
    description="Returns full class analytics: distribution, leaderboard, trends, teacher performance.",
    responses={200: ClassDetailSerializer},
    operation_id="dashboard_classes_retrieve",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacherOrSchoolAdmin])
def class_detail(request, class_id):
    data = get_class_detail(class_id)
    if not data:
        return Response(
            {"error": "Class not found or you don't have access"},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(data)


@extend_schema(
    tags=["Dashboard"],
    summary="Get student profile",
    description="Returns student profile with academic history, risk score, interventions, and notes.",
    responses={200: StudentProfileSerializer},
    operation_id="dashboard_student_profile",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_profile(request, student_id):
    data = get_student_profile(student_id)
    if not data:
        return Response(
            {"error": "Student not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(data)


@extend_schema(
    tags=["Dashboard"],
    summary="Create student note",
    description="Add a note to a student's profile.",
    request=StudentNoteCreateSerializer,
    responses={201: StudentNoteSerializer},
    operation_id="dashboard_student_note_create",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def student_note_create(request, student_id):
    serializer = StudentNoteCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    note = add_student_note(
        student_id=student_id,
        author_id=request.user.id,
        note_text=serializer.validated_data["note"],
    )
    if note is None:
        return Response(
            {"error": "Could not create note"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(StudentNoteSerializer(note).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Dashboard"],
    summary="Get report summary",
    description="Returns filtered report with period comparison and insights.",
    responses={200: ReportSummarySerializer},
    operation_id="dashboard_report_view",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def report_view(request):
    filters = {
        "class_id": request.query_params.get("class_id"),
        "date_from": request.query_params.get("date_from"),
        "date_to": request.query_params.get("date_to"),
        "teacher_id": request.query_params.get("teacher_id"),
    }
    filters = {k: v for k, v in filters.items() if v}
    data = get_report_summary(filters)
    return Response(data)


@extend_schema(
    tags=["Dashboard"],
    summary="Export report",
    description="Export report as PDF or XLSX file.",
    responses={200: OpenApiResponse(description="PDF or XLSX file")},
    operation_id="dashboard_report_export",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def report_export(request):
    fmt = request.query_params.get("format")
    if fmt not in ("pdf", "xlsx"):
        return Response(
            {"error": "format must be 'pdf' or 'xlsx'"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    filters = {
        "class_id": request.query_params.get("class_id"),
        "date_from": request.query_params.get("date_from"),
        "date_to": request.query_params.get("date_to"),
    }
    filters = {k: v for k, v in filters.items() if v}

    if fmt == "pdf":
        pdf_bytes = generate_report_pdf(filters)
        response = Response(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="report.pdf"'
        return response
    else:
        buffer = generate_report_excel(filters)
        response = Response(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="report.xlsx"'
        return response


@extend_schema(
    tags=["Dashboard"],
    summary="Get risk summary",
    description="Returns risk tier breakdown and top at-risk students.",
    responses={200: RiskSummarySerializer},
    operation_id="dashboard_risk_summary",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacherOrSchoolAdmin])
def risk_summary(request):
    data = get_risk_summary()
    return Response(data)


@extend_schema(
    tags=["Dashboard"],
    summary="Dismiss insight",
    description="Dismiss a dashboard insight/alert.",
    request=None,
    responses={200: OpenApiResponse(response=DashboardInsightSerializer, description="Insight dismissed.")},
    operation_id="dashboard_insight_dismiss",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTeacherOrSchoolAdmin])
def insight_dismiss(request, insight_id):
    insight = dismiss_insight(insight_id, request.user)
    if insight is None:
        return Response(
            {"error": "Insight not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(
        {
            "id": insight.id,
            "is_dismissed": insight.is_dismissed,
            "dismissed_by": insight.dismissed_by.username
            if insight.dismissed_by
            else None,
            "dismissed_at": insight.dismissed_at.isoformat()
            if insight.dismissed_at
            else None,
        }
    )
