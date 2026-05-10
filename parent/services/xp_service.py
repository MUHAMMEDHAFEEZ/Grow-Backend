from django.db.models import Sum

from xp.models import XPTransaction


def get_total_xp(student_id: int) -> dict:
    result = XPTransaction.objects.filter(student_id=student_id).aggregate(
        total=Sum("xp")
    )
    total = result["total"] or 0
    return {"total": total}


def get_monthly_xp(student_id: int, year: int, month: int) -> dict:
    result = XPTransaction.objects.filter(
        student_id=student_id,
        created_at__year=year,
        created_at__month=month,
    ).aggregate(total=Sum("xp"))
    monthly_total = result["total"] or 0
    return {"total": monthly_total}


def get_xp_breakdown(student_id: int) -> dict:
    rows = (
        XPTransaction.objects.filter(student_id=student_id)
        .values("source")
        .annotate(total=Sum("xp"))
        .order_by("source")
    )
    breakdown = {}
    for row in rows:
        breakdown[row["source"]] = row["total"]
    return breakdown
