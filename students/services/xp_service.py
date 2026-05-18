from django.db.models import Sum
from django.db.models.functions import Coalesce

from xp.models import XPTransaction


def get_total_xp(student):
    result = XPTransaction.objects.filter(student=student).aggregate(
        total=Coalesce(Sum("xp_amount"), 0)
    )
    return result["total"] or 0


def award_xp(student, source_type, source_id, amount):
    existing = XPTransaction.objects.filter(
        student=student,
        source_type=source_type,
        source_id=source_id,
    ).exists()

    if existing:
        return None

    source_map = {
        "lesson": XPTransaction.Source.STUDY.value,
        "quiz": XPTransaction.Source.QUIZ.value,
        "assignment": XPTransaction.Source.ASSIGNMENT.value,
        "task": XPTransaction.Source.STUDY.value,
        "streak": XPTransaction.Source.ATTENDANCE.value,
    }
    return XPTransaction.objects.create(
        student=student,
        xp_amount=amount,
        source=source_map.get(source_type, XPTransaction.Source.STUDY.value),
        source_type=source_type,
        source_id=source_id,
    )
