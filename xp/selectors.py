from django.db.models import Sum, Count
from django.db.models.functions import Coalesce


def get_active_session(student):
    """Get student's currently active session."""
    from study_sessions.models import StudySession

    return StudySession.objects.filter(student=student, ended_at__isnull=True).first()


def get_xp_history(student, page=1, page_size=20, source=None):
    """
    Get XP transaction history for a student.

    Args:
        page: Page number (1-indexed)
        page_size: Items per page
        source: Optional filter by XP source

    Returns queryset ordered by most recent first.
    """
    from xp.models import XPTransaction

    queryset = XPTransaction.objects.filter(student=student)

    if source:
        queryset = queryset.filter(source=source)

    offset = (page - 1) * page_size

    return queryset.order_by("-created_at")[offset : offset + page_size]


def get_total_transactions(student):
    """Get total number of XP transactions for a student."""
    from xp.models import XPTransaction

    return XPTransaction.objects.filter(student=student).count()
