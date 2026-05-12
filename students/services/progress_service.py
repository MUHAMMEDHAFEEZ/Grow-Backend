from django.db import transaction

from courses.models import Course, CourseProgress, Lesson
from students.models import LessonCompletion


@transaction.atomic
def complete_lesson(student, lesson_id):
    lesson = Lesson.objects.select_related("course").get(id=lesson_id)
    course = lesson.course

    LessonCompletion.objects.get_or_create(
        student=student,
        lesson=lesson,
    )

    total_lessons = Lesson.objects.filter(course=course).count()
    completed_lessons = LessonCompletion.objects.filter(
        student=student,
        lesson__course=course,
    ).count()

    progress, _ = CourseProgress.objects.get_or_create(
        student=student,
        course=course,
    )

    percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
    progress.progress_percentage = percentage
    progress.save(update_fields=["progress_percentage"])

    return {
        "completion_percentage": round(percentage, 2),
        "completed_lessons": completed_lessons,
        "total_lessons": total_lessons,
    }
