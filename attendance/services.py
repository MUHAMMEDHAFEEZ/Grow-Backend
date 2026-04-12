from __future__ import annotations

import datetime
from typing import List

from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.selectors import get_parent_ids_for_student
from core.events import EventBus, Events
from core.exceptions import NotFound, PermissionDenied

from .models import AttendanceRecord

User = get_user_model()


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
            EventBus.publish(Events.ATTENDANCE_MARKED, {
                "record_id": obj.pk,
                "course_id": course.pk,
                "course_title": course.title,
                "student_id": rec["student_id"],
                "date": str(date),
                "status": rec["status"],
                "parent_ids": parent_ids,
            })
    return created
