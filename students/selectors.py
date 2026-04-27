from django.db.models import Sum, Count, Q, F
from django.db.models.functions import Coalesce
from django.utils import timezone

from xp.models import XPTransaction
from study_sessions.models import StudySession
from submissions.models import Submission
from assignments.models import Assignment


def get_student_xp(student):
    """Get total XP and daily XP change for a student."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = (today_start - timezone.timedelta(days=1))

    total_xp = XPTransaction.objects.filter(
        student=student
    ).aggregate(total=Coalesce(Sum('xp'), 0))['total'] or 0

    today_xp = XPTransaction.objects.filter(
        student=student,
        created_at__gte=today_start
    ).aggregate(total=Coalesce(Sum('xp'), 0))['total'] or 0

    yesterday_xp = XPTransaction.objects.filter(
        student=student,
        created_at__gte=yesterday_start,
        created_at__lt=today_start
    ).aggregate(total=Coalesce(Sum('xp'), 0))['total'] or 0

    return {
        'total': total_xp,
        'today': today_xp,
        'yesterday': yesterday_xp,
    }


def get_student_streak(student):
    """Calculate consecutive days of activity."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    xp_dates = XPTransaction.objects.filter(
        student=student
    ).dates('created_at', 'day').distinct()

    session_dates = StudySession.objects.filter(
        student=student
    ).dates('started_at', 'day').distinct()

    all_activity_dates = set(
        list(xp_dates.values_list('created_at', flat=True)) +
        list(session_dates.values_list('started_at', flat=True))
    )

    if not all_activity_dates:
        return 0

    sorted_dates = sorted(all_activity_dates, reverse=True)
    streak = 0
    check_date = today_start.date() if today_start.date() in sorted_dates else None

    if check_date is None:
        yesterday = (today_start - timezone.timedelta(days=1)).date()
        if yesterday in sorted_dates:
            check_date = yesterday
        else:
            return 0

    current_date = check_date
    for date in sorted_dates:
        if date == current_date:
            streak += 1
            current_date -= timezone.timedelta(days=1)
        elif date < current_date:
            break

    return streak


def get_student_tasks_today(student):
    """Get assignments due today with submission status."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timezone.timedelta(days=1)

    assignments = Assignment.objects.filter(
        due_date__gte=today_start,
        due_date__lt=today_end,
        course__grade=student.grade
    ).select_related('course')

    tasks = []
    for assignment in assignments:
        submission = Submission.objects.filter(
            student=student,
            assignment=assignment
        ).first()

        tasks.append({
            'id': assignment.id,
            'title': assignment.title,
            'subject': assignment.course.name if assignment.course else None,
            'due_date': assignment.due_date,
            'status': submission.status if submission else 'pending',
        })

    return tasks


def get_student_weekly_hours(student):
    """Calculate weekly study hours."""
    now = timezone.now()
    week_start = now - timezone.timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    sessions = StudySession.objects.filter(
        student=student,
        started_at__gte=week_start
    )

    total_seconds = sessions.aggregate(
        total=Coalesce(Sum('duration'), 0)
    )['total'] or 0

    total_hours = total_seconds / 3600

    return {
        'total_hours': round(total_hours, 2),
        'goal_hours': 10,
        'percentage': min(int((total_hours / 10) * 100), 100),
    }


def get_leaderboard(limit=10):
    """Get top students by XP."""
    from accounts.models import User

    top_students = XPTransaction.objects.values(
        'student__id',
        'student__student_profile__full_name'
    ).annotate(
        total_xp=Sum('xp')
    ).order_by('-total_xp')[:limit]

    return list(top_students)


def get_student_rank(student):
    """Get student's rank by XP."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("""
            WITH xp_ranks AS (
                SELECT 
                    student_id,
                    SUM(xp) as total_xp,
                    ROW_NUMBER() OVER (ORDER BY SUM(xp) DESC) as rank
                FROM xp_xptransaction
                WHERE student_id = %s
                GROUP BY student_id
            )
            SELECT rank FROM xp_ranks WHERE student_id = %s
        """, [student.id, student.id])

        result = cursor.fetchone()
        if result:
            return result[0]

    student_xp = XPTransaction.objects.filter(
        student=student
    ).aggregate(total=Coalesce(Sum('xp'), 0))['total'] or 0

    if student_xp == 0:
        return 0

    higher_count = XPTransaction.objects.values('student').annotate(
        total_xp=Sum('xp')
    ).filter(total_xp__gt=student_xp).count()

    return higher_count + 1


def get_upcoming_session(student):
    """Get upcoming study session."""
    now = timezone.now()

    session = StudySession.objects.filter(
        student=student,
        started_at__gt=now
    ).order_by('started_at').first()

    if session:
        end_time = session.started_at + timezone.timedelta(seconds=session.duration)
        return {
            'title': 'Study Session',
            'scheduled_at': session.started_at,
            'time_range': f"{session.started_at.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
        }

    return None