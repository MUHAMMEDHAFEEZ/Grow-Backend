from django.db import transaction

from core.exceptions import Conflict, ValidationError
from students.models import Student
from students.services import _check_rate_limit, _record_failed_attempt, _reset_attempts


@transaction.atomic
def link_student_by_id(*, parent, school_id, full_name, student_id, grade_id):
    _check_rate_limit(parent)

    try:
        student = Student.objects.select_for_update().get(student_id=student_id)
    except Student.DoesNotExist:
        _record_failed_attempt(parent)
        raise ValidationError("Information does not match any student.")

    if student.school_id != school_id:
        _record_failed_attempt(parent)
        raise ValidationError("Information does not match any student.")

    if student.grade_id != grade_id:
        _record_failed_attempt(parent)
        raise ValidationError("Information does not match any student.")

    if student.full_name.strip().lower() != full_name.strip().lower():
        _record_failed_attempt(parent)
        raise ValidationError("Information does not match any student.")

    if student.parent is not None and student.parent != parent:
        _record_failed_attempt(parent)
        raise Conflict("This student is already linked to another parent.")

    _reset_attempts(parent)
    student.parent = parent
    student.save(update_fields=["parent"])

    return student
