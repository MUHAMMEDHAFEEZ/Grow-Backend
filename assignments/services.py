from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone

from core.events import EventBus, Events
from core.exceptions import NotFound, PermissionDenied, ValidationError

from courses.selectors import is_enrolled
from .models import Assignment

User = get_user_model()


def create_assignment(
    *, teacher: User, course_id: int, title: str, description: str, due_date
) -> Assignment:
    from courses.models import Course

    if due_date < timezone.now():
        raise ValidationError("Due date must be in the future")
    if not teacher.is_teacher:
        raise PermissionDenied("Only teachers can create assignments.")
    try:
        course = Course.objects.get(pk=course_id, teacher=teacher)
    except Course.DoesNotExist:
        raise NotFound("Course not found or you do not own it.")
    assignment = Assignment.objects.create(
        course=course,
        title=title,
        description=description,
        due_date=due_date,
        created_by=teacher,
    )
    EventBus.publish(
        Events.ASSIGNMENT_CREATED,
        {
            "assignment_id": assignment.pk,
            "course_id": course.pk,
            "course_title": course.title,
            "title": assignment.title,
            "due_date": str(assignment.due_date),
            "teacher_id": teacher.pk,
        },
    )
    return assignment


def update_assignment(*, assignment_id: int, teacher: User, **fields) -> Assignment:
    try:
        assignment = Assignment.objects.select_related("course").get(pk=assignment_id)
    except Assignment.DoesNotExist:
        raise NotFound("Assignment not found.")
    if assignment.course.teacher_id != teacher.pk:
        raise PermissionDenied("You do not own this assignment's course.")
    for key, value in fields.items():
        setattr(assignment, key, value)
    assignment.save()
    return assignment


def delete_assignment(*, assignment_id: int, teacher: User) -> None:
    try:
        assignment = Assignment.objects.select_related("course").get(pk=assignment_id)
    except Assignment.DoesNotExist:
        raise NotFound("Assignment not found.")
    if assignment.course.teacher_id != teacher.pk:
        raise PermissionDenied("You do not own this assignment's course.")
    assignment.delete()
