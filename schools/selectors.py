from datetime import timedelta
from typing import Any

from django.db.models import Count, Min, Sum
from django.utils import timezone

from schools.models import Class, Grade
from xp.models import XPTransaction


def get_grades_for_school(school_id: int | None = None):
    qs = Grade.objects.all()
    if school_id is not None:
        qs = qs.filter(school_id=school_id)
    else:
        qs = qs.filter(school__isnull=True)

    ids = (
        qs.values("level")
        .annotate(min_id=Min("id"))
        .values_list("min_id", flat=True)
    )
    return Grade.objects.filter(id__in=ids).order_by("level")


def get_classes_for_school(school_id: int):
    return (
        Class.objects.filter(school_id=school_id)
        .select_related("grade")
        .annotate(student_count=Count("students"))
        .order_by("grade__level", "name")
    )


def get_class_detail(class_id: int) -> dict[str, Any]:
    class_obj = (
        Class.objects.select_related("school", "grade")
        .filter(id=class_id)
        .first()
    )
    if not class_obj:
        return {}

    from students.models import Student

    students_qs = Student.objects.filter(class_fk=class_obj)
    student_count = students_qs.count()

    active_cutoff = timezone.now() - timedelta(minutes=15)
    active_count = students_qs.filter(
        user__last_login__gte=active_cutoff
    ).count()

    teacher_ids = (
        class_obj.school.courses
        .filter(grade__level=class_obj.grade.level)
        .values("teacher_id")
        .distinct()
    )
    from accounts.models import User
    teacher_count = teacher_ids.count()
    assigned_teachers = list(
        User.objects.filter(id__in=teacher_ids).values(
            "id", "username", "email"
        )
    )

    top_performance = list(
        XPTransaction.objects.filter(
            student__student_profile__class_fk=class_obj
        )
        .values("student__username")
        .annotate(total_xp=Sum("xp"))
        .order_by("-total_xp")[:10]
    )

    return {
        "id": class_obj.id,
        "name": class_obj.name,
        "grade_name": class_obj.grade.name,
        "grade_level": class_obj.grade.level,
        "school_name": class_obj.school.name,
        "student_count": student_count,
        "teacher_count": teacher_count,
        "active_students": active_count,
        "top_performance": [
            {
                "student_name": item["student__username"],
                "total_xp": item["total_xp"],
            }
            for item in top_performance
        ],
        "assigned_teachers": assigned_teachers,
    }
