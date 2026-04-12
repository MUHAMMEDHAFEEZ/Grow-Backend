from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from .models import Grade

User = get_user_model()


def get_grades_for_student(student_id: int) -> QuerySet[Grade]:
    return (
        Grade.objects.filter(submission__student_id=student_id)
        .select_related("submission__assignment__course", "submission__student", "graded_by")
    )


def get_grades_for_course(course_id: int) -> QuerySet[Grade]:
    return (
        Grade.objects.filter(submission__assignment__course_id=course_id)
        .select_related("submission__student", "submission__assignment")
    )
