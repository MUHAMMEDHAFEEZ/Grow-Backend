from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Count, QuerySet

from .models import StudentTask

User = get_user_model()


def get_tasks_for_student(
    student: User, *, status: str | None = None,
    course_id: int | None = None,
) -> QuerySet[StudentTask]:
    qs = StudentTask.objects.filter(student=student)
    if status:
        qs = qs.filter(status=status)
    if course_id:
        qs = qs.filter(course_id=course_id)
    return qs.select_related("course").order_by("-created_at")


def get_task_summary_for_course(course_id: int) -> list[dict]:
    """Return per-student task completion counts for a course's enrolled students."""
    from courses.models import StudentCourse

    students = (
        StudentCourse.objects.filter(course_id=course_id, is_active=True)
        .select_related("student")
    )

    rows = (
        StudentTask.objects.filter(course_id=course_id)
        .values("student_id", "status")
        .annotate(count=Count("id"))
    )

    summary_map: dict[int, dict] = {}
    for r in rows:
        sid = r["student_id"]
        if sid not in summary_map:
            summary_map[sid] = {"completed": 0, "pending": 0, "total": 0}
        summary_map[sid][r["status"]] = r["count"]
        summary_map[sid]["total"] += r["count"]

    result = []
    for sc in students:
        sid = sc.student_id
        s = summary_map.get(sid, {"completed": 0, "pending": 0, "total": 0})
        result.append({
            "student_id": sid,
            "student_name": sc.student.get_full_name() or sc.student.username,
            "completed_count": s["completed"],
            "pending_count": s["pending"],
            "total_count": s["total"],
        })
    return result
