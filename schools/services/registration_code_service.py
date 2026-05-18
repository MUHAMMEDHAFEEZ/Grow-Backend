from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction

from core.exceptions import ValidationError
from schools.models import RegistrationCode

User = get_user_model()


@transaction.atomic
def validate_and_consume_code(code: str, school_id: int, code_type: str, user: User) -> RegistrationCode:
    # Phase 1: find any unused code matching this code string and type
    code_obj = (
        RegistrationCode.objects.select_for_update()
        .filter(code=code, code_type=code_type, is_used=False)
        .select_related("grade")
        .first()
    )
    if not code_obj:
        raise ValidationError("Invalid or already used code.")

    # Phase 2: verify the code belongs to the selected school
    if code_obj.school_id != school_id:
        raise ValidationError(
            "This code does not belong to the selected school."
        )

    code_obj.is_used = True
    code_obj.used_by = user
    code_obj.save(update_fields=["is_used", "used_by"])

    return code_obj
