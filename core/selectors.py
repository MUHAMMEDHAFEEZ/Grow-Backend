from __future__ import annotations

from django.db.models import QuerySet

from .models import ActivityLog


def get_logs(
    *,
    actor_id: int | None = None,
    event_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 100,
) -> QuerySet[ActivityLog]:
    """Query activity logs with optional filters."""
    qs = ActivityLog.objects.select_related("actor").all()
    if actor_id is not None:
        qs = qs.filter(actor_id=actor_id)
    if event_type is not None:
        qs = qs.filter(event_type=event_type)
    if from_date is not None:
        qs = qs.filter(created_at__gte=from_date)
    if to_date is not None:
        qs = qs.filter(created_at__lte=to_date)
    return qs[:limit]
