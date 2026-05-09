from __future__ import annotations

from django.contrib.auth import get_user_model

from .models import Notification

User = get_user_model()


def create_notification(
    *, recipient_id: int, title: str, body: str, event_type: str,
    related_course_id: int | None = None,
    related_content_id: int | None = None,
) -> Notification:
    return Notification.objects.create(
        recipient_id=recipient_id, title=title, body=body, event_type=event_type,
        related_course_id=related_course_id,
        related_content_id=related_content_id,
    )


def mark_read(*, notification_id: int, user: User) -> Notification:
    from core.exceptions import NotFound, PermissionDenied
    try:
        notif = Notification.objects.get(pk=notification_id)
    except Notification.DoesNotExist:
        raise NotFound("Notification not found.")
    if notif.recipient_id != user.pk:
        raise PermissionDenied()
    notif.is_read = True
    notif.save(update_fields=["is_read"])
    return notif


def mark_all_read(*, user: User) -> int:
    return Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
