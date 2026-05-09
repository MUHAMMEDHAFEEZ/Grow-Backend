"""
dashboard/handlers.py — EventBus subscribers for dashboard events.

Subscribes to grade and attendance events to trigger risk score recalculation.
Registered in AppConfig.ready().
"""

import logging

from core.events import EventBus

logger = logging.getLogger(__name__)


def on_submission_graded(payload: dict) -> None:
    """Recalculate risk score when a submission is graded."""
    student_id = payload.get("student_id")
    if student_id:
        try:
            from .selectors import calculate_risk_score
            risk = calculate_risk_score(student_id)
            if risk["score"] > 60:
                logger.info(
                    "Student %d risk score: %d (%s)",
                    student_id,
                    risk["score"],
                    risk["tier"],
                )
        except Exception:
            logger.exception("Error recalculating risk score for student %d", student_id)


def on_attendance_marked(payload: dict) -> None:
    """Recalculate risk score when attendance is marked."""
    student_id = payload.get("student_id")
    if student_id:
        try:
            from .selectors import calculate_risk_score
            risk = calculate_risk_score(student_id)
            if risk["score"] > 60:
                logger.info(
                    "Student %d risk score after attendance: %d (%s)",
                    student_id,
                    risk["score"],
                    risk["tier"],
                )
        except Exception:
            logger.exception("Error recalculating risk score for student %d", student_id)


def register_handlers() -> None:
    """Register all dashboard event handlers with the EventBus."""
    EventBus.subscribe("submission_graded", on_submission_graded)
    EventBus.subscribe("attendance_marked", on_attendance_marked)
    logger.info("Dashboard event handlers registered")
