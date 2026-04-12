from django.db.models import QuerySet

from courses.selectors import is_enrolled
from .models import Assignment


def get_assignments_for_course(course_id: int) -> QuerySet[Assignment]:
    return Assignment.objects.filter(course_id=course_id).select_related("course", "created_by")


def get_assignment(assignment_id: int) -> Assignment:
    from core.exceptions import NotFound
    try:
        return Assignment.objects.select_related("course", "created_by").get(pk=assignment_id)
    except Assignment.DoesNotExist:
        raise NotFound("Assignment not found.")
