from django.db.models import Sum, Count
from django.db.models.functions import Coalesce


class XPError(Exception):
    """Base exception for XP errors."""

    pass


class InvalidXPValueError(XPError):
    """Raised when XP value is invalid."""

    pass


class InvalidSourceError(XPError):
    """Raised when source is invalid."""

    pass


def add_xp(student, xp_amount, source):
    """
    Add XP to a student's total.

    Args:
        student: User instance
        xp_amount: Integer XP amount (must be positive)
        source: XPTransaction.Source value

    Returns the XPTransaction instance.

    Raises:
        InvalidXPValueError: If xp_amount is negative or zero
        InvalidSourceError: If source is not valid
    """
    from xp.models import XPTransaction

    if xp_amount <= 0:
        raise InvalidXPValueError("XP amount must be positive")

    if source not in XPTransaction.Source.values:
        raise InvalidSourceError(f"Invalid source: {source}")

    transaction = XPTransaction.objects.create(
        student=student, xp=xp_amount, source=source
    )
    return transaction


def award_study_session_xp(session):
    """
    Award XP for a completed study session.
    Called when a session ends.

    Args:
        session: StudySession instance

    Returns the XPTransaction or None if no XP earned.
    """
    if session.xp_earned > 0:
        return add_xp(
            student=session.student,
            xp_amount=session.xp_earned,
            source=XPTransaction.Source.STUDY,
        )
    return None


def get_total_xp(student):
    """
    Get total XP for a student using aggregation.

    Returns dict with total_xp and transaction_count.
    """
    from xp.models import XPTransaction

    result = XPTransaction.objects.filter(student=student).aggregate(
        total_xp=Coalesce(Sum("xp"), 0), transaction_count=Count("id")
    )
    return {
        "total_xp": result["total_xp"],
        "transaction_count": result["transaction_count"],
    }


def get_xp_breakdown(student):
    """
    Get XP breakdown by source.

    Returns dict mapping source to XP total.
    """
    from django.db import connection
    from xp.models import XPTransaction

    result = (
        XPTransaction.objects.filter(student=student)
        .values("source")
        .annotate(total=Sum("xp"))
    )

    breakdown = {source: 0 for source in XPTransaction.Source.values}
    for row in result:
        breakdown[row["source"]] = row["total"] or 0

    return breakdown
