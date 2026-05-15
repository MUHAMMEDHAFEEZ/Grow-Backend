from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction

from core.exceptions import ValidationError
from schools.models import RegistrationCode

User = get_user_model()


@transaction.atomic
def validate_and_consume_code(code: str, school_id: int, code_type: str, user: User) -> RegistrationCode:
    code_obj = (
        RegistrationCode.objects.select_for_update()
        .filter(code=code, school_id=school_id, code_type=code_type, is_used=False)
        .select_related("grade")
        .first()
    )
    if not code_obj:
        raise ValidationError("Invalid or already used code.")

    code_obj.is_used = True
    code_obj.used_by = user
    code_obj.save(update_fields=["is_used", "used_by"])

    return code_obj
