"""
courses/selectors.py — Read-only query helpers.
"""

from __future__ import annotations

import datetime

from django.contrib.auth import get_user_model
from django.db.models import QuerySet, Sum
from django.utils import timezone

from .models import (
    Course,
    CourseProgress,
    Lesson,
    LessonActivity,
    Quiz,
    QuizAttempt,
    StudentCourse,
)

User = get_user_model()


def get_all_courses() -> QuerySet[Course]:
    return Course.objects.select_related("teacher").all()


def get_courses_for_teacher(teacher: User) -> QuerySet[Course]:
    return Course.objects.filter(teacher=teacher).select_related("teacher")


def get_enrolled_courses(student: User) -> QuerySet[Course]:
    profile = getattr(student, 'student_profile', None)
    if profile is None or profile.grade is None:
        return Course.objects.none()
    return (
        Course.objects.filter(
            grade__level=profile.grade.level,
            is_published=True,
        )
        .select_related("teacher")
        .distinct()
    )


def get_course_students(course_id: int) -> QuerySet:
    return StudentCourse.objects.filter(course_id=course_id).select_related("student")


def get_lessons_for_course(course_id: int) -> QuerySet[Lesson]:
    return Lesson.objects.filter(course_id=course_id).order_by("order")


def get_enrolled_student_ids(course_id: int) -> list[int]:
    """Return a flat list of student user IDs enrolled in the given course."""
    return list(
        StudentCourse.objects.filter(course_id=course_id).values_list(
            "student_id", flat=True
        )
    )


def is_enrolled(student: User, course_id: int) -> bool:
    return StudentCourse.objects.filter(
        student=student, course_id=course_id
    ).exists()


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
    return StudentCourse.objects.filter(
        student=student, course_id=course_id, is_active=True
    ).exists()


def get_courses_for_grade(grade_id: int) -> QuerySet[Course]:
    """Return courses filtered by grade."""
    return Course.objects.filter(grade_id=grade_id).select_related("teacher")


def get_course_progress(student: User, course: Course) -> CourseProgress | None:
    return CourseProgress.objects.filter(student=student, course=course).first()


def get_all_progress_for_course(course: Course) -> QuerySet[CourseProgress]:
    return CourseProgress.objects.filter(course=course).select_related("student")


def get_attempt_count(student: User, quiz: Quiz) -> int:
    return QuizAttempt.objects.filter(student=student, quiz=quiz).count()


def get_quiz_attempts(student: User, quiz: Quiz) -> QuerySet[QuizAttempt]:
    return QuizAttempt.objects.filter(student=student, quiz=quiz).order_by("-attempt_number")


def get_best_score(student: User, quiz: Quiz) -> float | None:
    result = (
        QuizAttempt.objects.filter(student=student, quiz=quiz)
        .order_by("-score")
        .values_list("score", flat=True)
        .first()
    )
    return float(result) if result is not None else None


def get_quiz_attempts_for_teacher(quiz: Quiz) -> QuerySet[QuizAttempt]:
    return QuizAttempt.objects.filter(quiz=quiz).select_related("student")


def get_lesson_activity(
    student: User, lesson: Lesson
) -> LessonActivity | None:
    return (
        LessonActivity.objects.filter(student=student, lesson=lesson)
        .select_related("student", "lesson__course")
        .first()
    )


def get_all_activity_for_course(
    student: User, course: Course
) -> QuerySet[LessonActivity]:
    return LessonActivity.objects.filter(
        student=student, lesson__course=course
    ).select_related("lesson")


def get_total_study_time(
    student: User,
    from_date: datetime.datetime | None = None,
    to_date: datetime.datetime | None = None,
) -> int:
    """Return total study time in seconds for a student, optionally date-filtered."""
    qs = CourseProgress.objects.filter(student=student)
    if from_date:
        qs = qs.filter(last_activity__gte=from_date)
    if to_date:
        qs = qs.filter(last_activity__lte=to_date)
    result = qs.aggregate(total=Sum("study_time_seconds"))
    return result["total"] or 0


def get_course_completion_rate(course: Course) -> float:
    """Percentage of engaged students who completed the course."""
    qs = CourseProgress.objects.filter(course=course)
    total_engaged = qs.exclude(
        completion_status=CourseProgress.CompletionStatus.NOT_STARTED
    ).count()
    if total_engaged == 0:
        return 0.0
    completed = qs.filter(
        completion_status=CourseProgress.CompletionStatus.COMPLETED
    ).count()
    return round((completed / total_engaged) * 100, 2)


def get_engagement_rate(course: Course) -> float:
    """Percentage of enrolled students who have at least one progress record."""
    enrolled = StudentCourse.objects.filter(course=course).count()
    if enrolled == 0:
        return 0.0
    engaged = CourseProgress.objects.filter(course=course).count()
    return round((engaged / enrolled) * 100, 2)


def get_study_time_trend(
    student: User,
    interval: str = "daily",
) -> list[dict]:
    """Return study time aggregation per day for a student."""
    qs = CourseProgress.objects.filter(student=student).values("last_activity", "study_time_seconds")
    # Group by date — fetch raw and group in Python for SQLite compatibility
    from collections import defaultdict
    buckets: dict[str, int] = defaultdict(int)
    for cp in qs:
        if cp["last_activity"]:
            key = cp["last_activity"].strftime("%Y-%m-%d")
            buckets[key] += cp["study_time_seconds"]
    return [{"date": k, "study_time_seconds": v} for k, v in sorted(buckets.items())]


def get_completion_rate(course: Course) -> dict[str, int]:
    qs = CourseProgress.objects.filter(course=course)
    return {
        "not_started": qs.filter(completion_status=CourseProgress.CompletionStatus.NOT_STARTED).count(),
        "in_progress": qs.filter(completion_status=CourseProgress.CompletionStatus.IN_PROGRESS).count(),
        "completed": qs.filter(completion_status=CourseProgress.CompletionStatus.COMPLETED).count(),
    }
