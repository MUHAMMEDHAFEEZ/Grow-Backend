from django.db.models import Avg, Count, Q
from django.db.models.functions import Coalesce
from django.utils import timezone

from grades.models import Grade


def get_student_grades(student_id: int):
    return Grade.objects.filter(
        submission__student_id=student_id,
        submission__status="graded"
    ).select_related("submission__assignment__course")


def get_student_sessions(student_id: int):
    from study_sessions.models import StudySession
    return StudySession.objects.filter(
        student_id=student_id,
        ended_at__isnull=False
    ).select_related("student")


def get_student_sessions_this_week(student_id: int):
    from study_sessions.models import StudySession
    week_ago = timezone.now() - timezone.timedelta(days=7)
    return StudySession.objects.filter(
        student_id=student_id,
        ended_at__isnull=False,
        started_at__gte=week_ago
    )


def get_student_attendance(student_id: int):
    from attendance.models import AttendanceRecord
    return AttendanceRecord.objects.filter(student_id=student_id)


def get_student_submissions(student_id: int):
    from submissions.models import Submission
    return Submission.objects.filter(student_id=student_id)


def get_student_courses(student_id: int):
    from courses.models import Enrollment
    return Enrollment.objects.filter(student_id=student_id).select_related("course")


def get_student_assignments(student_id: int):
    from submissions.models import Submission
    return Submission.objects.filter(student_id=student_id).select_related("assignment__course")