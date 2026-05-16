from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsStudent
from students.selectors import get_student_settings
from students.serializers.settings_serializers import StudentSettingsSerializer


@extend_schema(
    tags=["Student Settings"],
    summary="Student settings",
    description="Get profile settings with aggregated stats.",
    responses={200: StudentSettingsSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStudent])
def student_settings_view(request):
    data = get_student_settings(request.user)
    serializer = StudentSettingsSerializer(data)
    return Response(serializer.data)
