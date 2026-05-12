from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.permissions import IsTeacher
from teachers.models import TeacherNotification
from teachers.serializers import TeacherNotificationSerializer


@extend_schema(
    tags=["Teacher Notifications"],
    summary="List notifications",
    responses={200: TeacherNotificationSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def list_notifications(request: Request) -> Response:
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))
    start = (page - 1) * page_size
    end = start + page_size
    qs = TeacherNotification.objects.filter(teacher=request.user).order_by("-created_at")
    count = qs.count()
    items = qs[start:end]
    return Response({
        "count": count,
        "next": f"?page={page + 1}&page_size={page_size}" if end < count else None,
        "previous": f"?page={page - 1}&page_size={page_size}" if page > 1 else None,
        "results": TeacherNotificationSerializer(items, many=True).data,
    })


@extend_schema(
    tags=["Teacher Notifications"],
    summary="Mark notification as read",
    request=None,
    responses={200: OpenApiResponse(description="Marked as read.")},
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsTeacher])
def mark_read(request: Request, notification_id: int) -> Response:
    updated = TeacherNotification.objects.filter(
        id=notification_id, teacher=request.user
    ).update(is_read=True)
    if not updated:
        return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response({"detail": "Marked as read."})
