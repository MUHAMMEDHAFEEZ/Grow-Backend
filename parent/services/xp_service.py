from django.db.models import Sum
from django.utils import timezone

from xp.models import XPTransaction


def get_total_xp(student_id: int) -> dict:
    total = XPTransaction.objects.filter(student_id=student_id).aggregate(
        total=Sum("xp_amount")
    )["total"] or 0

    now = timezone.now()
    this_month = XPTransaction.objects.filter(
        student_id=student_id,
        created_at__year=now.year,
        created_at__month=now.month,
    ).aggregate(total=Sum("xp_amount"))["total"] or 0

    last_month = now.month - 1 or 12
    last_month_year = now.year if now.month > 1 else now.year - 1
    prev_month = XPTransaction.objects.filter(
        student_id=student_id,
        created_at__year=last_month_year,
        created_at__month=last_month,
    ).aggregate(total=Sum("xp_amount"))["total"] or 0

    return {"total": total, "change": float(this_month - prev_month)}


def get_monthly_xp(student_id: int, year: int, month: int) -> dict:
    result = XPTransaction.objects.filter(
        student_id=student_id,
        created_at__year=year,
        created_at__month=month,
    ).aggregate(total=Sum("xp_amount"))
    monthly_total = result["total"] or 0
    return {"total": monthly_total}


def get_xp_breakdown(student_id: int) -> dict:
    rows = (
        XPTransaction.objects.filter(student_id=student_id)
        .values("source")
        .annotate(total=Sum("xp_amount"))
        .order_by("source")
    )
    breakdown = {}
    for row in rows:
        breakdown[row["source"]] = row["total"]
    return breakdown
