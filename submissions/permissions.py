from rest_framework import permissions

from courses.selectors import is_enrolled


class IsCourseTeacher(permissions.BasePermission):
    """Check if user is the teacher of the course for an assignment."""

    def has_object_permission(self, request, view, obj):
        assignment = getattr(obj, 'assignment', None)
        if assignment is None:
            assignment = obj

        course = getattr(assignment, 'course', None)
        if course is None:
            from assignments.models import Assignment
            if hasattr(assignment, 'assignment_id'):
                assignment = Assignment.objects.filter(pk=assignment.assignment_id).first()
                course = assignment.course if assignment else None

        if course is None:
            return False

        return course.teacher_id == request.user.id


class IsEnrolledStudent(permissions.BasePermission):
    """Check if student is enrolled in the course."""

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        assignment = getattr(obj, 'assignment', None)
        if assignment is None:
            assignment = obj

        course = getattr(assignment, 'course', None)
        if course is None:
            from assignments.models import Assignment
            if hasattr(assignment, 'assignment_id'):
                assignment = Assignment.objects.filter(pk=assignment.assignment_id).first()
                course = assignment.course if assignment else None

        if course is None:
            return False

        return is_enrolled(student=request.user, course_id=course.id)


class CanViewSubmission(permissions.BasePermission):
    """Teacher can view all, student can view own only."""

    def has_object_permission(self, request, view, obj):
        student = getattr(obj, 'student', None)
        if student and student.id == request.user.id:
            return True

        assignment = getattr(obj, 'assignment', None)
        if assignment is None:
            assignment = obj

        course = getattr(assignment, 'course', None)
        if course is None:
            from assignments.models import Assignment
            if hasattr(assignment, 'assignment_id'):
                assignment = Assignment.objects.filter(pk=assignment.assignment_id).select_related('course').first()
                course = assignment.course if assignment else None

        if course is None:
            return False

        return course.teacher_id == request.user.id