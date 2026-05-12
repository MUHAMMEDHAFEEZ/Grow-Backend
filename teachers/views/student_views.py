from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.permissions import IsTeacher
from teachers.selectors import get_teacher_students
from teachers.serializers import TeacherStudentListSerializer


@extend_schema(
    tags=["Teacher Students"],
    summary="List students with performance stats",
    responses={200: TeacherStudentListSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def list_students(request: Request) -> Response:
    grade = request.query_params.get("grade")
    search = request.query_params.get("search")
    students = get_teacher_students(request.user, grade=grade, search=search)
    total = len(students)
    need_att = sum(1 for s in students if s["status"] == "needs_attention")
    avg_perf = round(sum(s["avg_score_pct"] for s in students) / total, 2) if total > 0 else 0
    avg_att = round(sum(s["attendance_rate"] for s in students) / total, 2) if total > 0 else 0
    return Response(TeacherStudentListSerializer({
        "avg_performance": avg_perf,
        "avg_attendance": avg_att,
        "total_students": total,
        "need_attention": need_att,
        "students": students,
    }).data)
