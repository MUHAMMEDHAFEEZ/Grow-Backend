from django.db.models import QuerySet

from schools.models import RegistrationCode


def get_available_code(code: str, school_id: int, code_type: str) -> RegistrationCode | None:
    return RegistrationCode.objects.filter(
        code=code, school_id=school_id, code_type=code_type, is_used=False
    ).select_related("grade", "school").first()


def get_available_codes(school_id: int, code_type: str) -> QuerySet[RegistrationCode]:
    return RegistrationCode.objects.filter(
        school_id=school_id, code_type=code_type, is_used=False
    ).select_related("grade")
