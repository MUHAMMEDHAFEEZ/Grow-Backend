"""
accounts/handlers.py — Event handler registrations for the accounts domain.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def handle_school_member_added(payload: dict) -> None:
    """
    Handles the SCHOOL_MEMBER_ADDED event.

    Payload fields:
        school_id (int): PK of the school the user joined.
        user_id   (int): PK of the user who joined.
        role      (str): The membership role assigned ("student" | "teacher" | "admin").

    This handler runs synchronously in-process (EventBus is not async/Celery).
    Keep it fast; defer heavy work to a background task if needed in future.
    """
    school_id = payload.get("school_id")
    user_id = payload.get("user_id")
    role = payload.get("role")

    logger.info(
        "school_member_added: user_id=%s joined school_id=%s as role=%s",
        user_id,
        school_id,
        role,
    )
