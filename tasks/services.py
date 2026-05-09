from __future__ import annotations

from django.contrib.auth import get_user_model

from .models import StudentTask

User = get_user_model()

TASK_TITLE_TEMPLATES = {
    "lesson": "Study Lesson: {title}",
    "quiz": "Complete Quiz: {title}",
    "assignment": "Submit Assignment: {title}",
}


def create_tasks_for_content(
    *, student_ids: list[int], course_id: int,
    content_type: str, content_id: int, title: str,
) -> int:
    template = TASK_TITLE_TEMPLATES.get(content_type, "{title}")
    task_title = template.format(title=title)

    objs = [
        StudentTask(
            student_id=sid,
            course_id=course_id,
            content_type=content_type,
            content_id=content_id,
            title=task_title,
        )
        for sid in student_ids
    ]
    created = StudentTask.objects.bulk_create(objs, ignore_conflicts=True)
    return len(created)


def complete_task(*, student: User, content_type: str, content_id: int) -> StudentTask | None:
    from django.utils import timezone

    updated = StudentTask.objects.filter(
        student=student,
        content_type=content_type,
        content_id=content_id,
        status=StudentTask.Status.PENDING,
    ).update(status=StudentTask.Status.COMPLETED, completed_at=timezone.now())
    if updated:
        return StudentTask.objects.get(
            student=student, content_type=content_type, content_id=content_id
        )
    return None
