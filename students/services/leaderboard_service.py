from django.db.models import Sum, F
from django.db.models.functions import Coalesce

from xp.models import XPTransaction


def get_leaderboard(student):
    class_students = XPTransaction.objects.filter(
        student__student_profile__grade=student.student_profile.grade
    ).values("student", "student__username")

    leaderboard_data = (
        XPTransaction.objects.filter(
            student__student_profile__grade=student.student_profile.grade
        )
        .values("student", "student__username")
        .annotate(
            total_xp=Coalesce(Sum("xp_amount"), 0),
            earliest_xp=Sum("created_at"),
        )
        .order_by("-total_xp", "earliest_xp")
    )

    result = []
    for i, entry in enumerate(leaderboard_data):
        result.append({
            "rank": i + 1,
            "username": entry["student__username"],
            "total_xp": entry["total_xp"],
        })

    my_entry = next(
        (e for e in result if e["username"] == student.username), None
    )

    top_2 = result[:2]
    if my_entry and my_entry not in top_2:
        top_2.append(my_entry)

    return top_2
