"""
courses/selectors.py — Read-only query helpers.
"""

from __future__ import annotations

import datetime

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.utils import timezone

from .models import Course, Enrollment, Lesson

User = get_user_model()


def get_all_courses() -> QuerySet[Course]:
    return Course.objects.select_related("teacher").all()


def get_courses_for_teacher(teacher: User) -> QuerySet[Course]:
    return Course.objects.filter(teacher=teacher).select_related("teacher")


def get_enrolled_courses(student: User) -> QuerySet[Course]:
    return (
        Course.objects.filter(enrollments__student=student)
        .select_related("teacher")
        .distinct()
    )


def get_course_students(course_id: int) -> QuerySet:
    return Enrollment.objects.filter(course_id=course_id).select_related("student")


def get_lessons_for_course(course_id: int) -> QuerySet[Lesson]:
    return Lesson.objects.filter(course_id=course_id).order_by("order")


def get_enrolled_student_ids(course_id: int) -> list[int]:
    """Return a flat list of student user IDs enrolled in the given course."""
    return list(
        Enrollment.objects.filter(course_id=course_id).values_list(
            "student_id", flat=True
        )
    )


def is_enrolled(student: User, course_id: int) -> bool:
    return Enrollment.objects.filter(student=student, course_id=course_id).exists()


def get_lesson_or_404(lesson_id: int) -> Lesson:
    """
    Fetch a lesson by ID or raise NotFound.
    Selects related course for efficiency.
    """
    from core.exceptions import NotFound

    try:
        return Lesson.objects.select_related("course").get(pk=lesson_id)
    except Lesson.DoesNotExist:
        raise NotFound("Lesson not found.")


def is_student_enrolled_in_course(student: User, course_id: int) -> bool:
    """Check if student is enrolled in the given course."""
    return Enrollment.objects.filter(student=student, course_id=course_id).exists()
