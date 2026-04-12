"""
accounts/selectors.py — Read-only query helpers for the accounts domain.

These functions provide a cross-app-safe interface so other apps can read
parent/child/school data without importing accounts models directly.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model

from .models import ParentProfile, School

User = get_user_model()


def get_child_for_parent(parent_user: User) -> User | None:
    """Return the linked child User for a parent, or None if not linked."""
    profile = (
        ParentProfile.objects.select_related("child")
        .filter(parent=parent_user)
        .first()
    )
    return profile.child if profile else None


def get_parent_ids_for_student(student_id: int) -> list[int]:
    """Return a flat list of parent user IDs linked to the given student."""
    return list(
        ParentProfile.objects.filter(child_id=student_id).values_list("parent_id", flat=True)
    )


def get_school_for_admin(admin_user: User) -> School | None:
    """Return the School owned by the given school admin, or None."""
    return School.objects.filter(created_by=admin_user).first()
