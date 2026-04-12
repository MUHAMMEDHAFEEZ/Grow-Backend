from django.db.models import QuerySet
from .models import Notification


def get_notifications_for_user(user_id: int) -> QuerySet[Notification]:
    return Notification.objects.filter(recipient_id=user_id).order_by("-created_at")


def get_unread_count(user_id: int) -> int:
    return Notification.objects.filter(recipient_id=user_id, is_read=False).count()
