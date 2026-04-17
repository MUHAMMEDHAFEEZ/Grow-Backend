from django.db.models import QuerySet
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
