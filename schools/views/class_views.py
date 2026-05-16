from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsSchoolAdmin
from schools.models import Class, School
from schools.selectors import get_class_detail
from schools.serializers.class_serializers import ClassDetailSerializer


@extend_schema(
    tags=["School Admin"],
    summary="Get class detail",
    description="Returns detailed analytics for a class, scoped to the school admin's school.",
    responses={200: ClassDetailSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def class_detail_view(request, class_id):
    school = School.objects.filter(admin=request.user).first()
    if not school:
        return Response(
            {"detail": "No school associated with your account."},
            status=status.HTTP_403_FORBIDDEN,
        )
    class_obj = Class.objects.filter(id=class_id, school=school).first()
    if not class_obj:
        return Response(
            {"error": "Class not found or you don't have access"},
            status=status.HTTP_404_NOT_FOUND,
        )
    data = get_class_detail(class_id)
    if not data:
        return Response(
            {"error": "Class not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(data)
