from django.db.models import Sum, Count
from django.db.models.functions import Coalesce


def get_study_sessions(student, page=1, page_size=20):
    """
    Get all study sessions for a student with pagination.

    Returns queryset ordered by most recent first.
    """
    from study_sessions.models import StudySession

    offset = (page - 1) * page_size

    return StudySession.objects.filter(student=student).order_by("-started_at")[
        offset : offset + page_size
    ]


def get_total_study_time(student):
    """
    Get total study time across all completed sessions.

    Returns dict with total_duration_seconds and session_count.
    """
    from study_sessions.models import StudySession

    result = StudySession.objects.filter(
        student=student, ended_at__isnull=False
    ).aggregate(total_duration=Coalesce(Sum("duration"), 0), session_count=Count("id"))

    total_seconds = result["total_duration"] or 0
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    return {
        "total_duration_seconds": total_seconds,
        "total_duration_formatted": f"{hours} hours {minutes} minutes",
        "session_count": result["session_count"],
    }


def get_session_count(student):
    """Get total number of sessions (completed) for a student."""
    from study_sessions.models import StudySession

    return StudySession.objects.filter(student=student, ended_at__isnull=False).count()
