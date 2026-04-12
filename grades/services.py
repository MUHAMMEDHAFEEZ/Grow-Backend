from __future__ import annotations

from django.contrib.auth import get_user_model

from core.events import EventBus, Events
from core.exceptions import Conflict, NotFound, PermissionDenied

from accounts.selectors import get_parent_ids_for_student
from .models import Grade

User = get_user_model()


def grade_submission(*, teacher: User, submission_id: int, score: float, feedback: str = "") -> Grade:
    from submissions.models import Submission  # lazy: grades depends on submissions (upstream)
    if not teacher.is_teacher:
        raise PermissionDenied("Only teachers can grade submissions.")
    try:
        submission = Submission.objects.select_related(
            "assignment__course", "student"
        ).get(pk=submission_id)
    except Submission.DoesNotExist:
        raise NotFound("Submission not found.")
    if submission.assignment.course.teacher_id != teacher.pk:
        raise PermissionDenied("You do not own this course.")
    if hasattr(submission, "grade"):
        raise Conflict("This submission is already graded.")

    grade = Grade.objects.create(
        submission=submission, score=score, feedback=feedback, graded_by=teacher
    )
    submission.status = Submission.Status.GRADED
    submission.save(update_fields=["status"])

    student = submission.student
    parent_ids = get_parent_ids_for_student(student.pk)

    EventBus.publish(Events.SUBMISSION_GRADED, {
        "grade_id": grade.pk,
        "submission_id": submission.pk,
        "assignment_title": submission.assignment.title,
        "course_title": submission.assignment.course.title,
        "score": float(score),
        "feedback": feedback,
        "student_id": student.pk,
        "student_username": student.username,
        "parent_ids": parent_ids,
        "teacher_id": teacher.pk,
    })
    return grade
