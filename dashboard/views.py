"""
dashboard/views.py — API endpoints for the dashboard.

No business logic here — delegates to selectors.py and services.py.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .permissions import IsSchoolAdmin, IsTeacherOfStudent, IsTeacherOrSchoolAdmin
from .selectors import (
    get_class_detail,
    get_classes_list,
    get_dashboard_overview,
    get_report_summary,
    get_risk_summary,
    get_student_profile,
)
from .serializers import (
    StudentNoteCreateSerializer,
    StudentNoteSerializer,
)
from .services import (
    add_student_note,
    dismiss_insight,
    generate_report_excel,
    generate_report_pdf,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacherOrSchoolAdmin])
def dashboard_overview(request):
    period = request.query_params.get("period", "month")
    academic_year = request.query_params.get("academic_year")
    data = get_dashboard_overview(period=period, academic_year=academic_year)
    return Response(data)


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


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacherOrSchoolAdmin])
def risk_summary(request):
    data = get_risk_summary()
    return Response(data)


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
