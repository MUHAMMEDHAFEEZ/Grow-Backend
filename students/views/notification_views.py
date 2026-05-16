from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsStudent
from students.serializers.notification_serializers import NotificationReadSerializer, NotificationSerializer
from students.models import StudentNotification


@extend_schema(
    tags=["Student Notifications"],
    summary="List notifications",
    description="Get paginated student notifications, newest first.",
    responses={200: NotificationSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStudent])
def notification_list_view(request):
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))

    queryset = StudentNotification.objects.filter(student=request.user).order_by("-created_at")
    offset = (page - 1) * page_size
    notifications = queryset[offset : offset + page_size]

    serializer = NotificationSerializer(notifications, many=True)
    return Response({
        "results": serializer.data,
        "count": queryset.count(),
    })


@extend_schema(
    tags=["Student Notifications"],
    summary="Mark notification as read",
    request=None,
    responses={200: NotificationReadSerializer},
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsStudent])
def mark_notification_read_view(request, notification_id):
    try:
        notification = StudentNotification.objects.get(
            id=notification_id, student=request.user
        )
    except StudentNotification.DoesNotExist:
        return Response({"error": "Notification not found"}, status=404)

    notification.is_read = True
    notification.save(update_fields=["is_read"])

    serializer = NotificationReadSerializer({"message": "Marked as read"})
    return Response(serializer.data)
