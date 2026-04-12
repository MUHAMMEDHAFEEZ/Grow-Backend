from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, help_text="Unique notification ID.")
    title = serializers.CharField(read_only=True, help_text="Short notification headline.")
    body = serializers.CharField(read_only=True, help_text="Full notification message body.")
    event_type = serializers.CharField(
        read_only=True,
        help_text=(
            "The domain event that triggered this notification. One of: "
            "`assignment_created`, `submission_created`, `submission_graded`, "
            "`attendance_marked`, `enrollment_created`."
        ),
    )
    is_read = serializers.BooleanField(
        read_only=True, help_text="Whether the user has read this notification."
    )
    created_at = serializers.DateTimeField(
        read_only=True, help_text="Timestamp when the notification was generated."
    )

    class Meta:
        model = Notification
        fields = ["id", "title", "body", "event_type", "is_read", "created_at"]
        read_only_fields = fields


class NotificationListResponseSerializer(serializers.Serializer):
    """Response envelope for GET /notifications/"""
    unread_count = serializers.IntegerField(
        help_text="Total number of unread notifications for the current user."
    )
    results = NotificationSerializer(
        many=True, help_text="Ordered list of notifications (newest first)."
    )


class MarkAllReadResponseSerializer(serializers.Serializer):
    """Response for POST /notifications/read-all/"""
    marked_read = serializers.IntegerField(
        help_text="Number of notifications that were marked as read by this operation."
    )
