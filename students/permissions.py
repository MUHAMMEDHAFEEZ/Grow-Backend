from rest_framework.permissions import BasePermission

from courses.models import Course


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "student")


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if hasattr(obj, "student"):
            return obj.student == user
        return obj == user


class BelongsToGrade(BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, "student_profile"):
            return False
        student = request.user.student_profile
        if isinstance(obj, Course):
            return obj.grade_id == student.grade_id
        if hasattr(obj, "course") and obj.course:
            return obj.course.grade_id == student.grade_id
        return True
