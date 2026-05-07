import datetime

from django.db.models import Count, QuerySet

from .models import AttendanceRecord


def get_attendance_for_course(course_id: int, date=None) -> QuerySet[AttendanceRecord]:
    qs = AttendanceRecord.objects.filter(course_id=course_id).select_related(
        "student", "course"
    )
    if date:
        qs = qs.filter(date=date)
    return qs


def get_attendance_for_student(student_id: int) -> QuerySet[AttendanceRecord]:
    return AttendanceRecord.objects.filter(student_id=student_id).select_related(
        "course"
    )


def get_attendance_summary(
    student_id: int, from_date: datetime.date, to_date: datetime.date
) -> dict[str, int]:
    """Return count of attendance records grouped by status."""
    qs = AttendanceRecord.objects.filter(
        student_id=student_id, date__gte=from_date, date__lte=to_date
    )
    counts = qs.values("status").annotate(count=Count("id"))
    result = {"present": 0, "absent": 0, "late": 0}
    for entry in counts:
        result[entry["status"]] = entry["count"]
    return result


def get_attendance_trend(
    course_id: int, from_date: datetime.date, to_date: datetime.date,
) -> list[dict]:
    """Return attendance aggregation per day for a course."""
    qs = (
        AttendanceRecord.objects.filter(
            course_id=course_id, date__gte=from_date, date__lte=to_date
        )
        .values("date", "status")
        .annotate(count=Count("id"))
        .order_by("date")
    )
    return list(qs)


def get_student_attendance_trend(
    student_id: int, from_date: datetime.date, to_date: datetime.date,
) -> list[dict]:
    """Return attendance aggregation per day for a student."""
    qs = (
        AttendanceRecord.objects.filter(
            student_id=student_id, date__gte=from_date, date__lte=to_date
        )
        .values("date", "status")
        .annotate(count=Count("id"))
        .order_by("date")
    )
    return list(qs)


def get_student_attendance_rate(
    student_id: int, course_id: int
) -> float:
    """Return percentage of days marked 'present' out of all attendance records."""
    total = AttendanceRecord.objects.filter(
        student_id=student_id, course_id=course_id
    ).count()
    if total == 0:
        return 0.0
    present = AttendanceRecord.objects.filter(
        student_id=student_id, course_id=course_id, status="present"
    ).count()
    return round((present / total) * 100, 2)


def get_attendance_for_student_course_date(
    student_id: int, course_id: int, date
) -> AttendanceRecord | None:
    """
    Get attendance record for a specific student, course, and date.
    Returns None if no record exists.
    """
    try:
        return AttendanceRecord.objects.select_related("student", "course").get(
            student_id=student_id,
            course_id=course_id,
            date=date,
        )
    except AttendanceRecord.DoesNotExist:
        return None
