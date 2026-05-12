from django.utils import timezone

from students.models import LoginHistory


def calculate_streak(student):
    login_dates = (
        LoginHistory.objects.filter(student=student)
        .values_list("login_date", flat=True)
        .order_by("-login_date")
    )

    if not login_dates:
        return 0

    today = timezone.now().date()
    streak = 0
    check_date = today

    for date in login_dates:
        if date == check_date:
            streak += 1
            check_date -= timezone.timedelta(days=1)
        elif date < check_date:
            break
        else:
            continue

    return streak
