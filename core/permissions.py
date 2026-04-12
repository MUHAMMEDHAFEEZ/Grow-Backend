"""
core/permissions.py — Reusable DRF permission classes.
"""
from rest_framework.permissions import BasePermission


class IsTeacher(BasePermission):
    message = "Only teachers can perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.role == "teacher")


class IsStudent(BasePermission):
    message = "Only students can perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.role == "student")


class IsParent(BasePermission):
    message = "Only parents can perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.role == "parent")


class IsSchoolAdmin(BasePermission):
    message = "Only school admins can perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.role == "school_admin")


class IsTeacherOrReadOnly(BasePermission):
    """Teachers can write; authenticated users can read."""

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.role == "teacher"
