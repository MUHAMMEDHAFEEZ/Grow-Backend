from datetime import date, timedelta

from django.db.models import Sum
from django.utils import timezone

from attendance.models import AttendanceRecord
from study_sessions.models import LoginHistory, StudySession


def get_study_streak(student_id: int) -> int:
    login_dates = (
        LoginHistory.objects.filter(student_id=student_id)
        .values_list("login_date", flat=True)
        .order_by("-login_date")
    )
    if not login_dates:
        return 0

    streak = 0
    today = timezone.now().date()
    seen = set(login_dates)

    for i in range(365):
        day = today - timedelta(days=i)
        if day in seen:
            streak += 1
        else:
            break

    return streak


def get_attendance_rate(student_id: int, year: int, month: int) -> float:
    sun_thu_count = 0
    for day in range(1, 32):
        try:
            d = date(year, month, day)
            if d.weekday() < 5:
                sun_thu_count += 1
        except ValueError:
            break

    if sun_thu_count == 0:
        return 0.0

    present_count = AttendanceRecord.objects.filter(
        student_id=student_id,
        date__year=year,
        date__month=month,
        status__in=["present", "late"],
    ).count()

    return round((present_count / sun_thu_count) * 100, 1)


def get_activity_calendar(student_id: int, year: int, month: int) -> list:
    present_dates = set(
        AttendanceRecord.objects.filter(
            student_id=student_id,
            date__year=year,
            date__month=month,
        ).values_list("date", flat=True)
    )

    calendar = []
    for day in range(1, 32):
        try:
            d = date(year, month, day)
        except ValueError:
            break

        status = "present" if d in present_dates else "absent"
        calendar.append({"date": d.isoformat(), "status": status})

    return calendar


def get_total_study_hours(student_id: int) -> float:
    result = StudySession.objects.filter(
        student_id=student_id,
        ended_at__isnull=False,
    ).aggregate(total=Sum("duration"))

    total_seconds = result["total"] or 0
    return round(total_seconds / 3600, 1)
