from __future__ import annotations

from django.contrib.auth import get_user_model

from core.events import EventBus, Events

from .services import log_event

User = get_user_model()


def _resolve_actor(actor_id: int) -> User | None:
    try:
        return User.objects.get(pk=actor_id)
    except User.DoesNotExist:
        return None


def on_course_opened(payload: dict) -> None:
    actor = _resolve_actor(payload.get("student_id", 0))
    if actor:
        log_event(
            actor=actor,
            event_type="course_opened",
            target_id=payload.get("course_id"),
            target_type="Course",
            metadata={"course_title": payload.get("course_title")},
        )


def on_lesson_completed(payload: dict) -> None:
    actor = _resolve_actor(payload.get("student_id", 0))
    if actor:
        log_event(
            actor=actor,
            event_type="lesson_completed",
            target_id=payload.get("lesson_id"),
            target_type="Lesson",
            metadata={
                "course_id": payload.get("course_id"),
                "lesson_title": payload.get("lesson_title"),
            },
        )


def on_quiz_submitted(payload: dict) -> None:
    actor = _resolve_actor(payload.get("student_id", 0))
    if actor:
        log_event(
            actor=actor,
            event_type="quiz_submitted",
            target_id=payload.get("quiz_id"),
            target_type="Quiz",
            metadata={
                "course_id": payload.get("course_id"),
                "score": payload.get("score"),
                "attempt_number": payload.get("attempt_number"),
            },
        )


def on_attendance_marked(payload: dict) -> None:
    actor = _resolve_actor(payload.get("student_id", 0))
    if actor:
        log_event(
            actor=actor,
            event_type="attendance_marked",
            target_id=payload.get("course_id"),
            target_type="Course",
            metadata={"status": payload.get("status")},
        )


def register_handlers() -> None:
    EventBus.subscribe(Events.COURSE_OPENED, on_course_opened)
    EventBus.subscribe(Events.LESSON_COMPLETED, on_lesson_completed)
    EventBus.subscribe(Events.QUIZ_SUBMITTED, on_quiz_submitted)
    EventBus.subscribe(Events.ATTENDANCE_MARKED, on_attendance_marked)

# TODO(analytics): Future analytics pipeline integration
# - Replace synchronous in-process handlers with async/background worker
# - Add batch aggregation for daily/weekly analytics reports
# - Implement event deduplication for idempotent processing
# - Consider using Django Q or Celery for async event processing
