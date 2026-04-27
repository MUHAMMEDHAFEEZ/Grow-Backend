from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone

from core.events import EventBus, Events
from core.exceptions import Conflict, NotFound, PermissionDenied

from courses.selectors import is_enrolled
from .models import Submission

User = get_user_model()


def submit_assignment(*, student: User, assignment_id: int, content: str) -> Submission:
    # Lazy import to avoid cross-app module-level dependency (assignments is upstream of submissions)
    from assignments.models import Assignment

    if not student.is_student:
        raise PermissionDenied("Only students can submit assignments.")
    try:
        assignment = Assignment.objects.select_related("course").get(pk=assignment_id)
    except Assignment.DoesNotExist:
        raise NotFound("Assignment not found.")
    if not is_enrolled(student=student, course_id=assignment.course_id):
        raise PermissionDenied("You are not enrolled in this course.")
    if assignment.due_date < timezone.now():
        raise PermissionDenied("Submission deadline has passed.")
    if Submission.objects.filter(assignment=assignment, student=student).exists():
        raise Conflict("You have already submitted this assignment.")
    submission = Submission.objects.create(assignment=assignment, student=student, content=content)
    EventBus.publish(Events.SUBMISSION_CREATED, {
        "submission_id": submission.pk,
        "assignment_id": assignment.pk,
        "assignment_title": assignment.title,
        "course_id": assignment.course_id,
        "student_id": student.pk,
        "student_username": student.username,
        "teacher_id": assignment.course.teacher_id,
    })
    return submission


def grade_submission(*, teacher: User, submission_id: int) -> Submission:
    from assignments.models import Assignment

    try:
        submission = Submission.objects.select_related("assignment__course").get(pk=submission_id)
    except Submission.DoesNotExist:
        raise NotFound("Submission not found.")

    if submission.assignment.course.teacher_id != teacher.id:
        raise PermissionDenied("You can only grade submissions for your own courses.")

    submission.status = Submission.Status.GRADED
    submission.save(update_fields=["status"])
    return submission
