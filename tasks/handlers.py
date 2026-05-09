"""
tasks/handlers.py — Subscribe to domain events to create and complete StudentTasks.

Registered when TasksConfig.ready() is called at startup.
"""

from __future__ import annotations

import logging

from core.events import EventBus, Events

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Handler implementations
# ---------------------------------------------------------------------------

def on_lesson_created(payload: dict) -> None:
    """Create a StudentTask for each enrolled student when a lesson is published."""
    from courses.selectors import get_enrolled_student_ids
    from tasks.services import create_tasks_for_content

    student_ids = get_enrolled_student_ids(payload["course_id"])
    if not student_ids:
        return
    created = create_tasks_for_content(
        student_ids=student_ids,
        course_id=payload["course_id"],
        content_type="lesson",
        content_id=payload["lesson_id"],
        title=payload["lesson_title"],
    )
    logger.info("Created %d tasks for lesson %d", created, payload["lesson_id"])


def on_quiz_created(payload: dict) -> None:
    """Create a StudentTask for each enrolled student when a quiz is published."""
    from courses.selectors import get_enrolled_student_ids
    from tasks.services import create_tasks_for_content

    student_ids = get_enrolled_student_ids(payload["course_id"])
    if not student_ids:
        return
    created = create_tasks_for_content(
        student_ids=student_ids,
        course_id=payload["course_id"],
        content_type="quiz",
        content_id=payload["quiz_id"],
        title=payload["quiz_title"],
    )
    logger.info("Created %d tasks for quiz %d", created, payload["quiz_id"])


def on_assignment_created(payload: dict) -> None:
    """Create a StudentTask for each enrolled student when an assignment is posted."""
    from courses.selectors import get_enrolled_student_ids
    from tasks.services import create_tasks_for_content

    student_ids = get_enrolled_student_ids(payload["course_id"])
    if not student_ids:
        return
    created = create_tasks_for_content(
        student_ids=student_ids,
        course_id=payload["course_id"],
        content_type="assignment",
        content_id=payload["assignment_id"],
        title=payload["title"],
    )
    logger.info("Created %d tasks for assignment %d", created, payload["assignment_id"])


def on_lesson_completed(payload: dict) -> None:
    """Mark the corresponding StudentTask as completed when a lesson is finished."""
    from django.contrib.auth import get_user_model
    from tasks.services import complete_task

    User = get_user_model()
    try:
        student = User.objects.get(pk=payload["student_id"])
    except User.DoesNotExist:
        logger.warning("Unknown student %d in lesson_completed", payload["student_id"])
        return
    task = complete_task(
        student=student, content_type="lesson", content_id=payload["lesson_id"]
    )
    if task:
        logger.info(
            "Completed task %d for student %d (lesson %d)",
            task.pk, payload["student_id"], payload["lesson_id"],
        )


def on_quiz_submitted(payload: dict) -> None:
    """Mark the corresponding StudentTask as completed when a quiz is submitted."""
    from django.contrib.auth import get_user_model
    from tasks.services import complete_task

    User = get_user_model()
    try:
        student = User.objects.get(pk=payload["student_id"])
    except User.DoesNotExist:
        logger.warning("Unknown student %d in quiz_submitted", payload["student_id"])
        return
    task = complete_task(
        student=student, content_type="quiz", content_id=payload["quiz_id"]
    )
    if task:
        logger.info(
            "Completed task %d for student %d (quiz %d)",
            task.pk, payload["student_id"], payload["quiz_id"],
        )


def on_submission_created(payload: dict) -> None:
    """Mark the assignment StudentTask as completed when a submission is created."""
    from django.contrib.auth import get_user_model
    from tasks.services import complete_task

    User = get_user_model()
    try:
        student = User.objects.get(pk=payload["student_id"])
    except User.DoesNotExist:
        logger.warning("Unknown student %d in submission_created", payload["student_id"])
        return
    task = complete_task(
        student=student, content_type="assignment", content_id=payload["assignment_id"]
    )
    if task:
        logger.info(
            "Completed task %d for student %d (assignment %d)",
            task.pk, payload["student_id"], payload["assignment_id"],
        )


# ---------------------------------------------------------------------------
# Registration — called from TasksConfig.ready()
# ---------------------------------------------------------------------------

def register_handlers() -> None:
    EventBus.subscribe(Events.LESSON_CREATED,     on_lesson_created)
    EventBus.subscribe(Events.QUIZ_CREATED,       on_quiz_created)
    EventBus.subscribe(Events.ASSIGNMENT_CREATED, on_assignment_created)
    EventBus.subscribe(Events.LESSON_COMPLETED,   on_lesson_completed)
    EventBus.subscribe(Events.QUIZ_SUBMITTED,     on_quiz_submitted)
    EventBus.subscribe(Events.SUBMISSION_CREATED, on_submission_created)
    logger.info("Task event handlers registered.")
