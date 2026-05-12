from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.permissions import IsTeacher
from teachers.selectors import get_dashboard_stats
from teachers.serializers import TeacherDashboardSerializer


@extend_schema(
    tags=["Teacher Dashboard"],
    summary="Teacher dashboard",
    responses={200: TeacherDashboardSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def dashboard(request: Request) -> Response:
    stats = get_dashboard_stats(request.user)
    return Response(TeacherDashboardSerializer(stats).data)
