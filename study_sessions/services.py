from django.utils import timezone
from datetime import timedelta


class SessionError(Exception):
    """Base exception for session errors."""

    pass


class ActiveSessionExistsError(SessionError):
    """Raised when attempting to start a new session while one is active."""

    pass


class NoActiveSessionError(SessionError):
    """Raised when no active session exists."""

    pass


def get_active_session(student):
    """
    Get the student's currently active session (if any).
    Returns None if no active session.
    """
    from study_sessions.models import StudySession

    return StudySession.objects.filter(student=student, ended_at__isnull=True).first()


def start_session(student):
    """
    Start a new study session for a student.

    Rules:
    - Student must NOT have an active session
    - Creates new session with current timestamp

    Returns the new StudySession.
    Raises ActiveSessionExistsError if session already active.
    """
    from study_sessions.models import StudySession

    active = get_active_session(student)
    if active:
        raise ActiveSessionExistsError(
            f"Student {student.id} already has an active session"
        )

    session = StudySession.objects.create(student=student)
    return session


def end_session(student):
    """
    End the student's current active session.

    Rules:
    - Must have an active session
    - Sets ended_at to now
    - Calculates duration in seconds
    - Awards XP based on duration

    Returns the updated StudySession with xp_earned.
    Raises NoActiveSessionError if no active session.

    XP Calculation:
    - Minimum: 5 minutes (300 seconds) to earn XP
    - Rate: 1 XP per minute (60 seconds)
    """
    from study_sessions.models import StudySession

    active = get_active_session(student)
    if not active:
        raise NoActiveSessionError(f"Student {student.id} has no active session")

    now = timezone.now()
    active.ended_at = now
    active.duration = int((now - active.started_at).total_seconds())

    if active.duration >= 300:
        active.xp_earned = active.duration // 60
    else:
        active.xp_earned = 0

    active.save()
    return active


def close_orphaned_sessions(timeout_hours=6):
    """
    Close sessions that have been open longer than the timeout.
    This handles cases where users forget to logout or close browser.

    Args:
        timeout_hours: Number of hours before a session is considered orphaned

    Returns:
        List of closed sessions
    """
    from study_sessions.models import StudySession

    threshold = timezone.now() - timedelta(hours=timeout_hours)
    orphaned = StudySession.objects.filter(
        ended_at__isnull=True, started_at__lt=threshold
    )

    closed = []
    for session in orphaned:
        session.ended_at = session.started_at + timedelta(hours=timeout_hours)
        session.duration = timeout_hours * 3600
        session.xp_earned = timeout_hours * 60
        session.save()
        closed.append(session)

    return closed
