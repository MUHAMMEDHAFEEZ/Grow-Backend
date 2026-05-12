from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from students.permissions import IsStudent
from students.serializers.dashboard_serializers import DashboardSerializer
from students.services.dashboard_service import get_dashboard


@extend_schema(
    tags=["Student Dashboard"],
    summary="Student dashboard",
    description="Get XP, streak, today's tasks, daily master, and leaderboard.",
    responses={200: DashboardSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStudent])
def student_dashboard_view(request):
    data = get_dashboard(request.user)
    serializer = DashboardSerializer(data)
    return Response(serializer.data)
