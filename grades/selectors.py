from django.contrib.auth import get_user_model
from django.db.models import Avg, QuerySet

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


def get_student_gpa(student_id: int) -> dict:
    result = Grade.objects.filter(
        submission__student_id=student_id,
        submission__status="graded"
    ).aggregate(
        gpa=Avg("score"),
        graded_count=Avg("id")
    )
    return {
        "student_id": student_id,
        "gpa": float(result["gpa"]) if result["gpa"] else 0.0,
        "graded_count": Grade.objects.filter(submission__student_id=student_id).count(),
    }


def get_course_gpa(course_id: int) -> dict:
    result = Grade.objects.filter(
        submission__assignment__course_id=course_id,
        submission__status="graded"
    ).aggregate(
        gpa=Avg("score"),
    )
    return {
        "course_id": course_id,
        "gpa": float(result["gpa"]) if result["gpa"] else 0.0,
    }
