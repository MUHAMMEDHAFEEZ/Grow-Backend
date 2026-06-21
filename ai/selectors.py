from django.db.models import Avg, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta


def get_student_courses(user):
    """Get student's enrolled courses."""
    from courses.models import StudentCourse

    enrollments = StudentCourse.objects.filter(
        student=user
    ).select_related('course', 'course__grade')

    courses = []
    for enrollment in enrollments:
        courses.append({
            'id': enrollment.course.id,
            'name': enrollment.course.name,
            'grade': enrollment.course.grade.name if enrollment.course.grade else None,
        })
    return courses


def get_student_grades(user):
    """Get student's grades across all courses."""
    from grades.models import Grade

    grades = Grade.objects.filter(
        submission__student=user
    ).select_related('submission__assignment__course').order_by('-graded_at')[:10]

    results = []
    for g in grades:
        results.append({
            'id': g.id,
            'course__name': g.submission.assignment.course.name if g.submission.assignment.course else None,
            'score': g.score,
            'created_at': g.graded_at,
        })
    return results


def get_student_assignments(user):
    """Get student's assignments and submission status."""
    from assignments.models import Assignment

    assignments = Assignment.objects.filter(
        course__student_courses__student=user
    ).select_related('course').prefetch_related(
        'submission_set'
    )

    results = []
    for assignment in assignments:
        submission = None
        for s in assignment.submission_set.all():
            if s.student_id == user.id:
                submission = s
                break

        results.append({
            'id': assignment.id,
            'title': assignment.title,
            'course': assignment.course.name if assignment.course else None,
            'due_date': assignment.due_date,
            'status': submission.status if submission else 'pending',
            'score': submission.score if submission else None,
        })
    return results


def get_student_sessions(user):
    """Get student's study sessions."""
    from study_sessions.models import StudySession

    now = timezone.now()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    sessions = StudySession.objects.filter(
        student=user,
        started_at__gte=week_start
    )

    total_seconds = sessions.aggregate(
        total=Coalesce(Sum('duration'), 0)
    )['total'] or 0

    return {
        'this_week_hours': round(total_seconds / 3600, 2),
        'session_count': sessions.count(),
    }


def get_student_attendance(user):
    """Get student's attendance rate."""
    from attendance.models import AttendanceRecord

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    records = AttendanceRecord.objects.filter(
        student=user,
        date__gte=month_start
    )

    total = records.count()
    if total == 0:
        return {'rate': 100, 'present': 0, 'total': 0}

    present = records.filter(status='present').count()
    rate = int((present / total) * 100) if total > 0 else 100

    return {'rate': rate, 'present': present, 'total': total}


def get_student_xp(user):
    """Get student's total XP."""
    from xp.models import XPTransaction

    total_xp = XPTransaction.objects.filter(
        student=user
    ).aggregate(total=Coalesce(Sum('xp_amount'), 0))['total'] or 0

    return {'total_xp': total_xp}


def compute_gpa(user):
    """Calculate student's GPA from grades."""
    from grades.models import Grade

    grades = Grade.objects.filter(submission__student=user)

    if not grades.exists():
        return 0

    avg_score = grades.aggregate(avg=Avg('score'))['avg'] or 0
    return round(avg_score, 1)


def identify_weak_subjects(user):
    """Identify subjects where student is struggling (score < 70)."""
    from grades.models import Grade

    weak_grades = Grade.objects.filter(
        submission__student=user,
        score__lt=70
    ).select_related('submission__assignment__course')

    weak_subjects = []
    for grade in weak_grades:
        course = grade.submission.assignment.course
        if course:
            weak_subjects.append(course.name)
    return list(set(weak_subjects))
