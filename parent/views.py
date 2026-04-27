from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsParent

from . import services
from .serializers import DashboardSerializer


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
        dashboard = services.get_parent_dashboard(
            parent=request.user,
            student_id=student_id,
        )
        return Response(DashboardSerializer(dashboard).data)