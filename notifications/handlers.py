"""
notifications/handlers.py — Subscribe to all domain events and create notifications.

These are registered when NotificationsConfig.ready() is called at startup.
"""
from __future__ import annotations

import logging

from core.events import EventBus, Events

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Handler implementations
# ---------------------------------------------------------------------------

def on_assignment_created(payload: dict) -> None:
    """Notify all enrolled students when a new assignment is posted."""
    from courses.selectors import get_enrolled_student_ids
    from notifications.services import create_notification

    course_id = payload["course_id"]
    student_ids = get_enrolled_student_ids(course_id)
    for sid in student_ids:
        create_notification(
            recipient_id=sid,
            title=f"New Assignment: {payload['title']}",
            body=f"A new assignment has been posted in '{payload['course_title']}'. Due: {payload['due_date']}",
            event_type=Events.ASSIGNMENT_CREATED,
        )


def on_submission_created(payload: dict) -> None:
    """Notify the teacher when a student submits an assignment."""
    from notifications.services import create_notification

    create_notification(
        recipient_id=payload["teacher_id"],
        title=f"New Submission: {payload['assignment_title']}",
        body=f"{payload['student_username']} submitted their work for '{payload['assignment_title']}'.",
        event_type=Events.SUBMISSION_CREATED,
    )


def on_submission_graded(payload: dict) -> None:
    """Notify student and their parent(s) when a submission is graded."""
    from notifications.services import create_notification

    body = (
        f"Your submission for '{payload['assignment_title']}' in '{payload['course_title']}' "
        f"has been graded. Score: {payload['score']}/100."
    )
    if payload.get("feedback"):
        body += f" Feedback: {payload['feedback']}"

    create_notification(
        recipient_id=payload["student_id"],
        title="Your submission was graded",
        body=body,
        event_type=Events.SUBMISSION_GRADED,
    )
    for parent_id in payload.get("parent_ids", []):
        create_notification(
            recipient_id=parent_id,
            title=f"Grade update for {payload['student_username']}",
            body=body,
            event_type=Events.SUBMISSION_GRADED,
        )


def on_attendance_marked(payload: dict) -> None:
    """Notify parent(s) if their child was marked absent."""
    from notifications.services import create_notification

    if payload["status"] != "absent":
        return
    for parent_id in payload.get("parent_ids", []):
        create_notification(
            recipient_id=parent_id,
            title="Absence Alert",
            body=(
                f"Your child was marked absent in '{payload['course_title']}' "
                f"on {payload['date']}."
            ),
            event_type=Events.ATTENDANCE_MARKED,
        )


def on_enrollment_created(payload: dict) -> None:
    """Confirm enrollment to the student."""
    from notifications.services import create_notification

    create_notification(
        recipient_id=payload["student_id"],
        title=f"Enrolled: {payload['course_title']}",
        body=f"You have been successfully enrolled in '{payload['course_title']}'.",
        event_type=Events.ENROLLMENT_CREATED,
    )


# ---------------------------------------------------------------------------
# Registration — called from NotificationsConfig.ready()
# ---------------------------------------------------------------------------

def register_handlers() -> None:
    EventBus.subscribe(Events.ASSIGNMENT_CREATED, on_assignment_created)
    EventBus.subscribe(Events.SUBMISSION_CREATED, on_submission_created)
    EventBus.subscribe(Events.SUBMISSION_GRADED,  on_submission_graded)
    EventBus.subscribe(Events.ATTENDANCE_MARKED,  on_attendance_marked)
    EventBus.subscribe(Events.ENROLLMENT_CREATED, on_enrollment_created)
    logger.info("Notification event handlers registered.")
