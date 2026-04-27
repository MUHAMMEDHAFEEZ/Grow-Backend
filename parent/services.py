from django.contrib.auth import get_user_model
from django.db.models import Avg
from django.utils import timezone
from datetime import timedelta

from core.exceptions import PermissionDenied

User = get_user_model()

WEEKLY_STUDY_GOAL_HOURS = 10
ENGAGEMENT_WEIGHTS = {
    "attendance": 0.4,
    "completion": 0.4,
    "activity": 0.2,
}


def get_parent_dashboard(parent: User, student_id: int) -> dict:
    from accounts.selectors import get_child_for_parent
    
    child = get_child_for_parent(parent)
    if not child or child.id != student_id:
        raise PermissionDenied("You can only view your child's dashboard.")
    
    return _compute_dashboard(student_id)


def _compute_dashboard(student_id: int) -> dict:
    return {
        "gpa": _compute_gpa(student_id),
        "study_hours": _compute_study_hours(student_id),
        "engagement": _compute_engagement(student_id),
        "subjects": _compute_subject_performance(student_id),
        "recent_activity": _compute_recent_activity(student_id),
    }


def _compute_gpa(student_id: int) -> dict:
    from grades.models import Grade
    from submissions.models import Submission
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    all_grades = Grade.objects.filter(
        submission__student_id=student_id,
        submission__status="graded"
    )
    
    current_avg = all_grades.aggregate(avg=Avg("score"))["avg"] or 0.0
    
    past_grades = Grade.objects.filter(
        submission__student_id=student_id,
        submission__status="graded",
        graded_at__lt=thirty_days_ago
    )
    past_avg = past_grades.aggregate(avg=Avg("score"))["avg"] or 0.0
    
    change = 0.0
    if past_avg > 0:
        change = float(current_avg) - float(past_avg)
    
    return {
        "value": float(current_avg),
        "change": round(change, 1),
    }


def _compute_study_hours(student_id: int) -> dict:
    from study_sessions.models import StudySession
    
    week_ago = timezone.now() - timedelta(days=7)
    
    total_seconds = StudySession.objects.filter(
        student_id=student_id,
        ended_at__isnull=False
    ).aggregate(total=models.Sum("duration"))["total"] or 0
    
    total_hours = total_seconds / 3600 if total_seconds else 0
    
    weekly_seconds = StudySession.objects.filter(
        student_id=student_id,
        ended_at__isnull=False,
        started_at__gte=week_ago
    ).aggregate(total=models.Sum("duration"))["total"] or 0
    
    weekly_hours = weekly_seconds / 3600 if weekly_seconds else 0
    
    progress = (weekly_hours / WEEKLY_STUDY_GOAL_HOURS * 100) if weekly_hours > 0 else 0
    
    return {
        "total": round(total_hours, 1),
        "weekly": round(weekly_hours, 1),
        "progress": round(min(progress, 100), 0),
    }


def _compute_engagement(student_id: int) -> int:
    from attendance.models import AttendanceRecord
    from submissions.models import Submission
    from courses.models import Enrollment
    
    attendance_records = AttendanceRecord.objects.filter(student_id=student_id)
    total_attendance = attendance_records.count()
    present_count = attendance_records.filter(present=True).count()
    attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0
    
    enrollments = Enrollment.objects.filter(student_id=student_id)
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
    from grades.models import Grade
    from submissions.models import Submission
    
    submissions = Submission.objects.filter(
        student_id=student_id,
        status="graded"
    ).select_related("assignment__course")
    
    course_grades = {}
    for sub in submissions:
        course = sub.assignment.course
        course_id = course.id
        if course_id not in course_grades:
            course_grades[course_id] = {"name": course.title, "scores": []}
        if sub.grade:
            course_grades[course_id]["scores"].append(float(sub.grade.score))
    
    subjects = []
    for course_id, data in course_grades.items():
        avg = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        label = _get_grade_label(avg)
        subjects.append({
            "name": data["name"],
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
            "title": f"Study session: {s.duration // 60} minutes",
            "timestamp": s.started_at.isoformat(),
        })
    
    submissions = Submission.objects.filter(
        student_id=student_id
    ).order_by("-submitted_at")[:3]
    for sub in submissions:
        activities.append({
            "type": "submission",
            "title": f"Assignment submitted: {sub.assignment.title}",
            "timestamp": sub.submitted_at.isoformat(),
        })
    
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return activities[:5]