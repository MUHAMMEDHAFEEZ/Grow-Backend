from django.db.models import QuerySet
from django.utils import timezone
from datetime import timedelta

from .models import Submission


def get_submissions_for_assignment(assignment_id: int) -> QuerySet[Submission]:
    return (
        Submission.objects.filter(assignment_id=assignment_id)
        .select_related("student", "assignment")
    )


def get_submission(submission_id: int) -> Submission:
    from core.exceptions import NotFound
    try:
        return Submission.objects.select_related("student", "assignment__course").get(pk=submission_id)
    except Submission.DoesNotExist:
        raise NotFound("Submission not found.")


def get_submissions_for_student(student_id: int) -> QuerySet[Submission]:
    return (
        Submission.objects.filter(student_id=student_id)
        .select_related("assignment", "assignment__course")
    )


def get_teacher_total_students(teacher_id: int) -> int:
    """Get unique students enrolled in teacher's courses."""
    from courses.models import StudentCourse
    from courses.models import Course
    course_ids = Course.objects.filter(teacher_id=teacher_id).values_list('id', flat=True)
    return StudentCourse.objects.filter(course_id__in=course_ids).values('student').distinct().count()


def get_teacher_total_courses(teacher_id: int) -> int:
    """Get total courses taught by teacher."""
    from courses.models import Course
    return Course.objects.filter(teacher_id=teacher_id).count()


def get_teacher_total_assignments(teacher_id: int) -> int:
    """Get total assignments created by teacher."""
    from assignments.models import Assignment
    return Assignment.objects.filter(course__teacher_id=teacher_id).count()


def get_teacher_active_assignments(teacher_id: int) -> int:
    """Get assignments with future due date."""
    from assignments.models import Assignment
    now = timezone.now()
    return Assignment.objects.filter(
        course__teacher_id=teacher_id,
        due_date__gt=now
    ).count()


def get_teacher_recent_activity(teacher_id: int, limit: int = 10) -> list:
    """Get recent submissions for teacher's assignments."""
    from assignments.models import Assignment
    from django.db.models import F

    assignment_ids = Assignment.objects.filter(
        course__teacher_id=teacher_id
    ).values_list('id', flat=True)

    submissions = Submission.objects.filter(
        assignment_id__in=assignment_ids
    ).select_related(
        'student',
        'assignment'
    ).order_by('-submitted_at')[:limit]

    results = []
    for sub in submissions:
        time_ago = timezone.now() - sub.submitted_at
        minutes = int(time_ago.total_seconds() / 60)
        if minutes < 60:
            time_ago_str = f"{minutes}m ago"
        elif minutes < 1440:
            time_ago_str = f"{minutes // 60}h ago"
        else:
            time_ago_str = f"{minutes // 1440}d ago"

        results.append({
            'student_name': sub.student.username,
            'assignment_title': sub.assignment.title,
            'status': sub.status,
            'grade': float(sub.normalized_score) if sub.normalized_score else None,
            'time_ago': time_ago_str,
        })

    return results
