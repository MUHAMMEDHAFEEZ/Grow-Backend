"""
courses/services.py — Business logic for courses, enrollments, and lessons.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model

from core.events import EventBus, Events
from core.exceptions import Conflict, NotFound, PermissionDenied

from .models import Course, Enrollment, Lesson

User = get_user_model()


def create_course(*, teacher: User, title: str, description: str = "") -> Course:
    if not teacher.is_teacher:
        raise PermissionDenied("Only teachers can create courses.")
    course = Course.objects.create(teacher=teacher, title=title, description=description)
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
    EventBus.publish(Events.ENROLLMENT_CREATED, {
        "enrollment_id": enrollment.pk,
        "course_id": course.pk,
        "course_title": course.title,
        "student_id": student.pk,
        "student_username": student.username,
    })
    return enrollment


def create_lesson(*, course_id: int, teacher: User, title: str, content: str, order: int = 0) -> Lesson:
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise NotFound("Course not found.")
    if course.teacher_id != teacher.pk:
        raise PermissionDenied("You do not own this course.")
    lesson = Lesson.objects.create(course=course, title=title, content=content, order=order)
    return lesson
