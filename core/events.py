"""
core/events.py — Synchronous in-process event bus.

Usage:
    # Publishing
    from core.events import EventBus
    EventBus.publish("submission_graded", {"submission_id": 1, "student_id": 2})

    # Subscribing (do this in app handlers.py, called from AppConfig.ready)
    from core.events import EventBus
    EventBus.subscribe("submission_graded", handle_graded)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Event name → list of handler callables
_registry: dict[str, list[Callable[[dict[str, Any]], None]]] = defaultdict(list)


class EventBus:
    @staticmethod
    def subscribe(event_name: str, handler: Callable[[dict[str, Any]], None]) -> None:
        """Register a handler for an event. Called once at startup."""
        _registry[event_name].append(handler)
        logger.debug(
            "EventBus: registered handler %s for '%s'", handler.__name__, event_name
        )

    @staticmethod
    def publish(event_name: str, payload: dict[str, Any]) -> None:
        """Dispatch event to all registered handlers synchronously."""
        handlers = _registry.get(event_name, [])
        if not handlers:
            logger.debug("EventBus: no handlers for '%s'", event_name)
            return
        for handler in handlers:
            try:
                handler(payload)
            except Exception:
                logger.exception(
                    "EventBus: handler %s raised an exception for event '%s'",
                    handler.__name__,
                    event_name,
                )

    @staticmethod
    def clear() -> None:
        """Clear all subscriptions — used in tests only."""
        _registry.clear()


# ---------------------------------------------------------------------------
# Event name constants — import these instead of raw strings
# ---------------------------------------------------------------------------


class Events:
    ASSIGNMENT_CREATED = "assignment_created"
    SUBMISSION_CREATED = "submission_created"
    SUBMISSION_GRADED = "submission_graded"
    ATTENDANCE_MARKED = "attendance_marked"
    ENROLLMENT_CREATED = "enrollment_created"
    SCHOOL_MEMBER_ADDED = "school_member_added"
    LESSON_JOINED = "lesson_joined"
