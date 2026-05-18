from django.utils import timezone

from assignments.models import Assignment
from courses.models import Quiz


def get_upcoming_schedule(student_id: int) -> list:
    now = timezone.now()
    items = []

    quizzes = Quiz.objects.filter(
        course__student_courses__student_id=student_id,
        course__student_courses__is_active=True,
    ).distinct()
    for q in quizzes:
        items.append({
            "type": "quiz",
            "id": q.id,
            "title": q.title,
            "date": q.created_at.isoformat(),
            "course": q.course.title if q.course else "",
        })

    assignments = Assignment.objects.filter(
        course__student_courses__student_id=student_id,
        course__student_courses__is_active=True,
        due_date__gte=now,
    ).distinct()
    for a in assignments:
        items.append({
            "type": "assignment",
            "id": a.id,
            "title": a.title,
            "date": a.due_date.isoformat(),
            "course": a.course.title if a.course else "",
        })

    items.sort(key=lambda x: x["date"])

    return items[:10]
