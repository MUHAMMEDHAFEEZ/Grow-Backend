from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone

from core.exceptions import PermissionDenied

from .gpa_service import get_cumulative_gpa

User = get_user_model()

WEEKLY_STUDY_GOAL_HOURS = 10
ENGAGEMENT_WEIGHTS = {
    "attendance": 0.4,
    "completion": 0.4,
    "activity": 0.2,
}


def get_parent_dashboard(parent: User, user_id: int) -> dict:
    from students.models import Student as StudentModel
    owns = StudentModel.objects.filter(user_id=user_id, parent=parent).exists()
    if not owns:
        raise PermissionDenied("You can only view your child's dashboard.")
    return _compute_dashboard(user_id)


def _compute_dashboard(student_id: int) -> dict:
    return {
        "gpa": get_cumulative_gpa(student_id),
        "study_hours": _compute_study_hours(student_id),
        "engagement": _compute_engagement(student_id),
        "subjects": _compute_subject_performance(student_id),
        "recent_activity": _compute_recent_activity(student_id),
    }


def _compute_study_hours(student_id: int) -> dict:
    from study_sessions.models import StudySession
    
    total_seconds = StudySession.objects.filter(
        student_id=student_id,
        ended_at__isnull=False
    ).aggregate(total=Sum("duration"))["total"] or 0
    
    total_hours = total_seconds / 3600 if total_seconds else 0
    
    two_weeks_ago = timezone.now() - timedelta(days=14)
    week_ago = timezone.now() - timedelta(days=7)
    
    prev_seconds = StudySession.objects.filter(
        student_id=student_id,
        ended_at__isnull=False,
        started_at__gte=two_weeks_ago,
        started_at__lt=week_ago
    ).aggregate(total=Sum("duration"))["total"] or 0
    
    this_week_seconds = StudySession.objects.filter(
        student_id=student_id,
        ended_at__isnull=False,
        started_at__gte=week_ago
    ).aggregate(total=Sum("duration"))["total"] or 0
    
    prev_hours = prev_seconds / 3600 if prev_seconds else 0
    this_week_hours = this_week_seconds / 3600 if this_week_seconds else 0
    
    return {
        "total": round(total_hours, 1),
        "change": round(this_week_hours - prev_hours, 1),
    }


def _compute_engagement(student_id: int) -> int:
    from attendance.models import AttendanceRecord
    from submissions.models import Submission
    from courses.models import StudentCourse
    
    attendance_records = AttendanceRecord.objects.filter(student_id=student_id)
    total_attendance = attendance_records.count()
    present_count = attendance_records.filter(status__in=["present", "late"]).count()
    attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0
    
    enrollments = StudentCourse.objects.filter(student_id=student_id)
    total_courses = enrollments.count()
    
    submissions = Submission.objects.filter(student_id=student_id)
    submitted_count = submissions.filter(status__in=["pending", "graded"]).count()
    completion_rate = (submitted_count / total_courses * 100) if total_courses > 0 else 0
    
    submissions_this_month = submissions.filter(
        submitted_at__gte=timezone.now() - timedelta(days=30)
    ).count()
    activity_rate = min(submissions_this_month * 10, 100)
    
    engagement = (
        ENGAGEMENT_WEIGHTS["attendance"] * attendance_rate +
        ENGAGEMENT_WEIGHTS["completion"] * completion_rate +
        ENGAGEMENT_WEIGHTS["activity"] * activity_rate
    )
    
    return round(min(engagement, 100), 0)


def _compute_subject_performance(student_id: int) -> list:
    from courses.models import Course
    from students.models import Student as StudentProfile
    from submissions.models import Submission

    profile = StudentProfile.objects.filter(user_id=student_id).first()
    course_list = Course.objects.none()
    if profile and profile.school_id:
        course_list = Course.objects.filter(
            school_id=profile.school_id,
            grade_id=profile.grade_id,
        )

    graded = Submission.objects.filter(
        student_id=student_id,
        status="graded",
    ).select_related("assignment__course")

    course_grades = {}
    for sub in graded:
        assignment = sub.assignment
        if not assignment or not assignment.course:
            continue
        course = assignment.course
        course_id = course.id
        if course_id not in course_grades:
            course_grades[course_id] = {"scores": []}
        if sub.raw_score is not None:
            course_grades[course_id]["scores"].append(float(sub.raw_score))

    subjects = []
    for course in course_list:
        data = course_grades.get(course.id, {"scores": []})
        avg = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        label = _get_grade_label(avg) if data["scores"] else "N/A"
        subjects.append({
            "name": course.title,
            "average": round(avg, 1),
            "grade": label,
        })

    return subjects


def _get_grade_label(average: float) -> str:
    if average >= 90:
        return "A"
    elif average >= 80:
        return "B"
    elif average >= 70:
        return "C"
    else:
        return "D"


def _compute_recent_activity(student_id: int) -> list:
    from study_sessions.models import StudySession
    from submissions.models import Submission
    
    activities = []
    
    sessions = StudySession.objects.filter(
        student_id=student_id
    ).order_by("-started_at")[:3]
    for s in sessions:
        activities.append({
            "type": "study_session",
            "title": f"Study session: {(s.duration or 0) // 60} minutes",
            "timestamp": s.started_at.isoformat(),
        })
    
    submissions = Submission.objects.filter(
        student_id=student_id
    ).order_by("-submitted_at")[:3]
    for sub in submissions:
        if not sub.assignment:
            continue
        activities.append({
            "type": "submission",
            "title": f"Assignment submitted: {sub.assignment.title}",
            "timestamp": sub.submitted_at.isoformat(),
        })
    
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return activities[:5]
