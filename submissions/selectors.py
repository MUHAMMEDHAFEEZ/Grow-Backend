from django.db.models import QuerySet

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
