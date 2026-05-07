from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import ActivityLog

User = get_user_model()


def log_event(
    *,
    actor: User,
    event_type: str,
    target_id: int | None = None,
    target_type: str | None = None,
    metadata: dict | None = None,
) -> ActivityLog:
    """Create an activity log entry."""
    return ActivityLog.objects.create(
        actor=actor,
        event_type=event_type,
        target_id=target_id,
        target_type=target_type,
        metadata=metadata,
    )


def prune_old_logs() -> int:
    """Delete activity logs older than 12 months. Returns count deleted."""
    cutoff = timezone.now() - timedelta(days=365)
    deleted, _ = ActivityLog.objects.filter(created_at__lt=cutoff).delete()
    return deleted
