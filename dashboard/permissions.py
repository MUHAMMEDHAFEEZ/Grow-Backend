"""
dashboard/permissions.py — Role-based access control for dashboard endpoints.
"""

from rest_framework import permissions

from courses.models import Course, Enrollment


class IsSchoolAdmin(permissions.BasePermission):
    """Allow only school_admin role."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "school_admin"


class IsTeacherOrSchoolAdmin(permissions.BasePermission):
    """Allow teacher (restricted to own classes) or school_admin."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == "school_admin":
            return True
        if request.user.role == "teacher":
            return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.role == "school_admin":
            return True
        if request.user.role == "teacher":
            if hasattr(obj, "teacher_id"):
                return obj.teacher_id == request.user.id
            if hasattr(obj, "id"):
                return Course.objects.filter(
                    id=obj.id, teacher=request.user
                ).exists()
        return False


class IsTeacherOfStudent(permissions.BasePermission):
    """Allow teacher only if they teach the student, or school_admin."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == "school_admin":
            return True
        if request.user.role == "teacher":
            student_id = view.kwargs.get("student_id")
            if student_id:
                return Enrollment.objects.filter(
                    course__teacher=request.user,
                    student_id=student_id,
                ).exists()
        return False

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
