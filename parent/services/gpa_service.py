from django.db.models import Avg
from django.utils import timezone

from grades.models import Grade


def get_cumulative_gpa(student_id: int) -> dict:
    all_grades = Grade.objects.filter(
        submission__student_id=student_id,
        submission__status="graded",
    )
    avg = all_grades.aggregate(avg=Avg("score"))["avg"] or 0.0

    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    past_grades = Grade.objects.filter(
        submission__student_id=student_id,
        submission__status="graded",
        graded_at__lt=thirty_days_ago,
    )
    past_avg = past_grades.aggregate(avg=Avg("score"))["avg"] or 0.0

    change = 0.0
    if past_avg > 0:
        change = float(avg) - float(past_avg)

    return {
        "value": float(avg),
        "change": round(change, 1),
    }


def get_monthly_gpas(student_id: int, year: int) -> list:
    grades = Grade.objects.filter(
        submission__student_id=student_id,
        submission__status="graded",
        graded_at__year=year,
    )

    monthly = {}
    for g in grades:
        month = g.graded_at.month
        if month not in monthly:
            monthly[month] = []
        monthly[month].append(float(g.score))

    result = []
    for month in range(1, 13):
        if month in monthly:
            scores = monthly[month]
            result.append({
                "month": month,
                "average": round(sum(scores) / len(scores), 1),
                "count": len(scores),
            })

    return result
