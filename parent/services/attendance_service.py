from datetime import date, timedelta

from django.db.models import Sum
from django.utils import timezone

from attendance.models import AttendanceRecord
from study_sessions.models import LoginHistory, StudySession


def get_study_streak(student_id: int) -> dict:
    login_dates = (
        LoginHistory.objects.filter(student_id=student_id)
        .values_list("login_date", flat=True)
        .order_by("-login_date")
    )
    if not login_dates:
        return {"total": 0, "change": 0}

    today = timezone.now().date()
    seen = set(login_dates)

    streak = 0
    for i in range(365):
        day = today - timedelta(days=i)
        if day in seen:
            streak += 1
        else:
            break

    yesterday_streak = 0
    yesterday = today - timedelta(days=1)
    for i in range(365):
        day = yesterday - timedelta(days=i)
        if day in seen:
            yesterday_streak += 1
        else:
            break

    return {"total": streak, "change": streak - yesterday_streak}


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
    from submissions.models import Submission
    from study_sessions.models import StudySession
    from courses.models import QuizAttempt
    from students.models import LessonCompletion

    active_dates = set()

    for rec in AttendanceRecord.objects.filter(
        student_id=student_id, date__year=year, date__month=month
    ).values_list("date", flat=True):
        active_dates.add(rec)

    for dt in Submission.objects.filter(
        student_id=student_id,
        submitted_at__year=year,
        submitted_at__month=month,
    ).values_list("submitted_at", flat=True):
        active_dates.add(dt.date())

    for dt in StudySession.objects.filter(
        student_id=student_id,
        started_at__year=year,
        started_at__month=month,
    ).values_list("started_at", flat=True):
        active_dates.add(dt.date())

    for dt in QuizAttempt.objects.filter(
        student_id=student_id,
        submitted_at__year=year,
        submitted_at__month=month,
    ).values_list("submitted_at", flat=True):
        active_dates.add(dt.date())

    for dt in LessonCompletion.objects.filter(
        student_id=student_id,
        completed_at__year=year,
        completed_at__month=month,
    ).values_list("completed_at", flat=True):
        active_dates.add(dt.date())

    calendar = []
    for day in range(1, 32):
        try:
            d = date(year, month, day)
        except ValueError:
            break

        status = "present" if d in active_dates else "absent"
        calendar.append({"date": d.isoformat(), "status": status})

    return calendar


def get_total_study_hours(student_id: int) -> dict:
    total_seconds = StudySession.objects.filter(
        student_id=student_id,
        ended_at__isnull=False,
    ).aggregate(total=Sum("duration"))["total"] or 0

    week_ago = timezone.now() - timedelta(days=7)
    prev_week_seconds = StudySession.objects.filter(
        student_id=student_id,
        ended_at__isnull=False,
        started_at__lt=week_ago,
    ).aggregate(total=Sum("duration"))["total"] or 0

    total = round(total_seconds / 3600, 1)
    prev = round(prev_week_seconds / 3600, 1)
    return {"total": total, "change": round(total - prev, 1)}
