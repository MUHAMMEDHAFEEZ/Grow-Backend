from django.db.models import Avg, Sum, Count, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta


def get_student_courses(student):
    """Get student's enrolled courses."""
    from courses.models import Enrollment

    enrollments = Enrollment.objects.filter(
        student=student
    ).select_related('course', 'course__grade')

    courses = []
    for enrollment in enrollments:
        courses.append({
            'id': enrollment.course.id,
            'name': enrollment.course.name,
            'grade': enrollment.course.grade.name if enrollment.course.grade else None,
        })
    return courses


def get_student_grades(student):
    """Get student's grades across all courses."""
    from grades.models import Grade

    grades = Grade.objects.filter(
        student=student
    ).select_related('course').order_by('-created_at')[:10]

    return list(grades.values('id', 'course__name', 'score', 'created_at'))


def get_student_assignments(student):
    """Get student's assignments and submission status."""
    from assignments.models import Assignment
    from submissions.models import Submission

    assignments = Assignment.objects.filter(
        course__enrollments__student=student
    ).select_related('course')

    results = []
    for assignment in assignments:
        submission = Submission.objects.filter(
            student=student,
            assignment=assignment
        ).first()

        results.append({
            'id': assignment.id,
            'title': assignment.title,
            'course': assignment.course.name if assignment.course else None,
            'due_date': assignment.due_date,
            'status': submission.status if submission else 'pending',
            'score': submission.score if submission else None,
        })
    return results


def get_student_sessions(student):
    """Get student's study sessions."""
    from study_sessions.models import StudySession

    now = timezone.now()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    sessions = StudySession.objects.filter(
        student=student,
        started_at__gte=week_start
    )

    total_seconds = sessions.aggregate(
        total=Coalesce(Sum('duration'), 0)
    )['total'] or 0

    return {
        'this_week_hours': round(total_seconds / 3600, 2),
        'session_count': sessions.count(),
    }


def get_student_attendance(student):
    """Get student's attendance rate."""
    from attendance.models import AttendanceRecord

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    records = AttendanceRecord.objects.filter(
        student=student,
        date__gte=month_start
    )

    total = records.count()
    if total == 0:
        return {'rate': 100, 'present': 0, 'total': 0}

    present = records.filter(status='present').count()
    rate = int((present / total) * 100) if total > 0 else 100

    return {'rate': rate, 'present': present, 'total': total}


def get_student_xp(student):
    """Get student's total XP."""
    from xp.models import XPTransaction

    total_xp = XPTransaction.objects.filter(
        student=student
    ).aggregate(total=Coalesce(Sum('xp'), 0))['total'] or 0

    return {'total_xp': total_xp}


def compute_gpa(student):
    """Calculate student's GPA from grades."""
    from grades.models import Grade

    grades = Grade.objects.filter(student=student)

    if not grades.exists():
        return 0

    avg_score = grades.aggregate(avg=Avg('score'))['avg'] or 0
    return round(avg_score, 1)


def identify_weak_subjects(student):
    """Identify subjects where student is struggling (score < 70)."""
    from grades.models import Grade

    weak_grades = Grade.objects.filter(
        student=student,
        score__lt=70
    ).select_related('course')

    weak_subjects = []
    for grade in weak_grades:
        if grade.course:
            weak_subjects.append(grade.course.name)
    return list(set(weak_subjects))