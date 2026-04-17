"""
attendance/domain.py — Domain objects for attendance feature.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class AttendanceResult:
    """
    Domain object returned by attendance service.
    Not an ORM instance — safe for API layer consumption.
    """

    lesson_id: int
    student_id: int
    status: str  # "present" | "late" | "absent"
    date: datetime.date
    is_new: bool  # True if first join, False if returning existing


@dataclass(frozen=True)
class LessonAttendanceSummary:
    """
    Domain object returned by teacher attendance view.
    Contains attendance summary for a lesson.
    """

    lesson_id: int
    lesson_title: str
    total_enrolled: int
    attendance: list[
        dict
    ]  # [{"student_id": int, "student_name": str, "status": str|None}, ...]
