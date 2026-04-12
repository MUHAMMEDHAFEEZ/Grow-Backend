from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import selectors, services
from .serializers import (
    MarkAllReadResponseSerializer,
    NotificationListResponseSerializer,
    NotificationSerializer,
)


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="List notifications",
        description=(
            "Returns all in-app notifications for the authenticated user, ordered newest first.\n\n"
            "The response includes an `unread_count` summary and the `results` list.\n\n"
            "**Notification event types:**\n"
            "| Event Type | Triggered By |\n"
            "|---|---|\n"
            "| `assignment_created` | Teacher posts a new assignment |\n"
            "| `submission_created` | Student submits an assignment |\n"
            "| `submission_graded`  | Teacher grades a submission |\n"
            "| `attendance_marked`  | Student marked absent |\n"
            "| `enrollment_created` | Student enrolls in a course |"
        ),
        responses={
            200: OpenApiResponse(
                response=NotificationListResponseSerializer,
                description="Notification inbox.",
            ),
        },
        examples=[
            OpenApiExample(
                "Notification List Response",
                value={
                    "unread_count": 2,
                    "results": [
                        {
                            "id": 10,
                            "title": "Your submission was graded",
                            "body": "Your submission for 'Lab Report' in 'Biology' has been graded. Score: 87/100.",
                            "event_type": "submission_graded",
                            "is_read": False,
                            "created_at": "2026-04-10T15:00:00Z",
                        },
                        {
                            "id": 9,
                            "title": "New Assignment: Math Quiz",
                            "body": "A new assignment has been posted in 'Mathematics'. Due: 2026-05-01.",
                            "event_type": "assignment_created",
                            "is_read": True,
                            "created_at": "2026-04-08T09:00:00Z",
                        },
                    ],
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def get(self, request: Request) -> Response:
        notifications = selectors.get_notifications_for_user(request.user.pk)
        unread_count = selectors.get_unread_count(request.user.pk)
        return Response({
            "unread_count": unread_count,
            "results": NotificationSerializer(notifications, many=True).data,
        })


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Mark a notification as read",
        description=(
            "Mark a single notification as read. "
            "The notification must belong to the authenticated user."
        ),
        request=None,
        responses={
            200: OpenApiResponse(response=NotificationSerializer, description="Notification marked as read."),
            403: OpenApiResponse(description="This notification does not belong to you."),
            404: OpenApiResponse(description="Notification not found."),
        },
    )
    def post(self, request: Request, pk: int) -> Response:
        notif = services.mark_read(notification_id=pk, user=request.user)
        return Response(NotificationSerializer(notif).data)


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Mark all notifications as read",
        description="Marks every unread notification for the authenticated user as read in a single call.",
        request=None,
        responses={
            200: OpenApiResponse(
                response=MarkAllReadResponseSerializer,
                description="All notifications marked as read.",
            ),
        },
        examples=[
            OpenApiExample(
                "Mark All Read Response",
                value={"marked_read": 4},
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request: Request) -> Response:
        count = services.mark_all_read(user=request.user)
        return Response({"marked_read": count})
