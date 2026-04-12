"""
accounts/selectors.py — Read-only query helpers for the accounts domain.

These functions provide a cross-app-safe interface so other apps can read
parent/child/school data without importing accounts models directly.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from .models import EnrollmentCode, ParentProfile, School, SchoolMembership

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


# ── Enrollment Code Selectors ─────────────────────────────────────────────────


def get_school_membership(*, user: User, school: School) -> SchoolMembership | None:
    """Return the SchoolMembership for a (user, school) pair, or None."""
    return SchoolMembership.objects.filter(user=user, school=school).first()


def get_teacher_membership(*, user: User) -> SchoolMembership | None:
    """Return the active TEACHER membership for a user, or None."""
    return SchoolMembership.objects.filter(
        user=user, role=SchoolMembership.Role.TEACHER
    ).first()


def get_enrollment_codes_for_school(
    *, school_id: int, admin: User
) -> QuerySet[EnrollmentCode]:
    """
    Return all EnrollmentCodes for the given school.
    Raises PermissionDenied if admin does not own the school.
    """
    from core.exceptions import NotFound, PermissionDenied

    try:
        school = School.objects.get(pk=school_id)
    except School.DoesNotExist:
        raise NotFound("School not found.")

    if school.created_by_id != admin.pk:
        raise PermissionDenied("You do not own this school.")

    return (
        EnrollmentCode.objects
        .filter(school=school)
        .select_related("used_by", "revoked_by")
        .order_by("-created_at")
    )
