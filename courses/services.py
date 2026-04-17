"""
courses/services.py — Business logic for courses, enrollments, and lessons.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone

from attendance.domain import AttendanceResult, LessonAttendanceSummary
from attendance.services import calculate_attendance_status, upsert_attendance
from core.events import EventBus, Events
from core.exceptions import Conflict, NotFound, PermissionDenied

from .models import Course, Enrollment, Lesson
from .selectors import (
    get_enrolled_student_ids,
    get_lesson_or_404,
    is_student_enrolled_in_course,
)

User = get_user_model()


def create_course(*, teacher: User, title: str, description: str = "") -> Course:
    if not teacher.is_teacher:
        raise PermissionDenied("Only teachers can create courses.")
    course = Course.objects.create(
        teacher=teacher, title=title, description=description
    )
    return course


def update_course(*, course_id: int, teacher: User, **fields) -> Course:
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise NotFound("Course not found.")
    if course.teacher_id != teacher.pk:
        raise PermissionDenied("You do not own this course.")
    for key, value in fields.items():
        setattr(course, key, value)
    course.save()
    return course


def delete_course(*, course_id: int, teacher: User) -> None:
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise NotFound("Course not found.")
    if course.teacher_id != teacher.pk:
        raise PermissionDenied("You do not own this course.")
    course.delete()


def enroll_student(*, course_id: int, student: User) -> Enrollment:
    if not student.is_student:
        raise PermissionDenied("Only students can enroll.")
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise NotFound("Course not found.")
    if Enrollment.objects.filter(course=course, student=student).exists():
        raise Conflict("Already enrolled in this course.")
    enrollment = Enrollment.objects.create(course=course, student=student)
    EventBus.publish(
        Events.ENROLLMENT_CREATED,
        {
            "enrollment_id": enrollment.pk,
            "course_id": course.pk,
            "course_title": course.title,
            "student_id": student.pk,
            "student_username": student.username,
        },
    )
    return enrollment


def create_lesson(
    *,
    course_id: int,
    teacher: User,
    title: str,
    content: str,
    order: int = 0,
    start_time=None,
    end_time=None,
) -> Lesson:
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise NotFound("Course not found.")
    if course.teacher_id != teacher.pk:
        raise PermissionDenied("You do not own this course.")
    lesson = Lesson.objects.create(
        course=course,
        title=title,
        content=content,
        order=order,
        start_time=start_time,
        end_time=end_time,
    )
    return lesson


def join_lesson(*, lesson_id: int, student: User) -> AttendanceResult:
    """
    Student joins a lesson and receives automatic attendance status.

    Business rules:
    - Server time is used for all calculations
    - Status calculation: present (within 10 min), late (>10 min), absent (after end)
    - Rejects early joins (before start_time)
    - Validates enrollment
    - Uses upsert to prevent duplicates
    """
    lesson = get_lesson_or_404(lesson_id)

    if not is_student_enrolled_in_course(student, lesson.course_id):
        from core.exceptions import PermissionDenied as PD

        raise PD("You are not enrolled in this course.")

    if not lesson.start_time or not lesson.end_time:
        from core.exceptions import ValidationError as VE

        raise VE("This lesson does not have a scheduled time.")

    current_time = timezone.now()
    status = calculate_attendance_status(
        current_time=current_time,
        start_time=lesson.start_time,
        end_time=lesson.end_time,
    )

    result = upsert_attendance(
        student=student,
        course=lesson.course,
        date=lesson.start_time.date(),
        status=status,
        lesson_id=lesson_id,
    )

    EventBus.publish(
        "lesson_joined",
        {
            "lesson_id": lesson_id,
            "student_id": student.pk,
            "status": status,
            "course_id": lesson.course_id,
        },
    )

    return result


def get_lesson_attendance_summary(
    *, lesson_id: int, teacher: User
) -> LessonAttendanceSummary:
    """
    Teacher views attendance for all enrolled students in a lesson.

    Returns summary with all enrolled students and their attendance status.
    """
    lesson = get_lesson_or_404(lesson_id)

    if lesson.course.teacher_id != teacher.pk:
        from core.exceptions import PermissionDenied as PD

        raise PD("You do not have permission to view this attendance.")

    enrolled_student_ids = get_enrolled_student_ids(lesson.course_id)
    total_enrolled = len(enrolled_student_ids)

    from attendance.selectors import get_attendance_for_course

    attendance_records = get_attendance_for_course(
        lesson.course_id, date=lesson.start_time.date()
    )

    attendance_by_student = {
        record.student_id: record.status for record in attendance_records
    }

    attendance_list = []
    for student_id in enrolled_student_ids:
        from accounts.selectors import get_user_by_id

        user = get_user_by_id(student_id)
        attendance_list.append(
            {
                "student_id": student_id,
                "student_name": user.get_full_name() or user.username,
                "status": attendance_by_student.get(student_id),
            }
        )

    return LessonAttendanceSummary(
        lesson_id=lesson_id,
        lesson_title=lesson.title,
        total_enrolled=total_enrolled,
        attendance=attendance_list,
    )
