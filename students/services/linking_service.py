from django.db import transaction

from core.exceptions import Conflict, ValidationError
from students.models import Student
from students.services import _check_rate_limit, _record_failed_attempt, _reset_attempts


@transaction.atomic
def link_student_by_enrollment(*, parent, school_id, full_name, enrollment_code, grade_id):
    _check_rate_limit(parent)

    student = Student.objects.select_for_update().filter(
        school_id=school_id,
        full_name__iexact=full_name.strip(),
        grade_id=grade_id,
        parent_access_code__isnull=False,
    ).first()

    if not student:
        _record_failed_attempt(parent)
        raise ValidationError("Information does not match any student.")

    if student.parent_access_code.lower() != enrollment_code.strip().lower():
        _record_failed_attempt(parent)
        raise ValidationError("Information does not match any student.")

    if student.parent is not None and student.parent != parent:
        _record_failed_attempt(parent)
        raise Conflict("This student is already linked to another parent.")

    _reset_attempts(parent)
    student.parent = parent
    student.parent_access_code = None
    student.save(update_fields=["parent", "parent_access_code"])

    return student
