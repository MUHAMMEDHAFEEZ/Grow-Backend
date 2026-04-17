from __future__ import annotations

import datetime
from typing import List

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from accounts.selectors import get_parent_ids_for_student
from core.events import EventBus, Events
from core.exceptions import NotFound, PermissionDenied, ValidationError

from .domain import AttendanceResult
from .models import AttendanceRecord

User = get_user_model()


GRACE_PERIOD_MINUTES = 10


def calculate_attendance_status(
    current_time: datetime.datetime,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
) -> str:
    """
    Calculate attendance status based on current time vs lesson times.

    @param current_time: Server time when student joins
    @param start_time: Lesson scheduled start time
    @param end_time: Lesson scheduled end time

    @returns: "present" | "late" | "absent"
    @raises ValidationError: if current_time is before start_time
    """
    if current_time < start_time:
        raise ValidationError("Cannot join lesson before scheduled start time.")

    grace_period_end = start_time + datetime.timedelta(minutes=GRACE_PERIOD_MINUTES)

    if current_time <= grace_period_end:
        return "present"
    elif current_time <= end_time:
        return "late"
    else:
        return "absent"


@transaction.atomic
def upsert_attendance(
    *,
    student: User,
    course,
    date: datetime.date,
    status: str,
    lesson_id: int,
) -> AttendanceResult:
    """
    Create or update an attendance record for a student.

    Uses upsert logic (update_or_create) to prevent duplicate records.
    Returns an AttendanceResult domain object.

    @param student: Student user
    @param course: Course instance
    @param date: Date of the lesson/attendance
    @param status: "present" | "late" | "absent"
    @param lesson_id: ID of the lesson (for domain object)

    @returns: AttendanceResult domain object
    """
    record, created = AttendanceRecord.objects.update_or_create(
        course=course,
        student=student,
        date=date,
        defaults={"status": status},
    )

    return AttendanceResult(
        lesson_id=lesson_id,
        student_id=student.pk,
        status=status,
        date=date,
        is_new=created,
    )


@transaction.atomic
def mark_attendance(
    *,
    teacher: User,
    course_id: int,
    date: datetime.date,
    records: List[dict],
) -> List[AttendanceRecord]:
    """
    records: [{"student_id": int, "status": "present"|"absent"|"late"}, ...]
    """
    from courses.models import Course  # lazy: attendance depends on courses (upstream)

    if not teacher.is_teacher:
        raise PermissionDenied("Only teachers can mark attendance.")
    try:
        course = Course.objects.get(pk=course_id, teacher=teacher)
    except Course.DoesNotExist:
        raise NotFound("Course not found or you do not own it.")

    created = []
    for rec in records:
        obj, _ = AttendanceRecord.objects.update_or_create(
            course=course,
            student_id=rec["student_id"],
            date=date,
            defaults={"status": rec["status"], "marked_by": teacher},
        )
        created.append(obj)
        if rec["status"] == AttendanceRecord.Status.ABSENT:
            parent_ids = get_parent_ids_for_student(rec["student_id"])
            EventBus.publish(
                Events.ATTENDANCE_MARKED,
                {
                    "record_id": obj.pk,
                    "course_id": course.pk,
                    "course_title": course.title,
                    "student_id": rec["student_id"],
                    "date": str(date),
                    "status": rec["status"],
                    "parent_ids": parent_ids,
                },
            )
    return created
