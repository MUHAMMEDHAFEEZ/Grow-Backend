from __future__ import annotations

from django.db import transaction

from schools.models import Class, School


def get_or_create_class(school: School, grade, letter: str) -> Class:
    name = f"Class {grade.level} {letter}"
    class_obj, _ = Class.objects.get_or_create(
        school=school,
        grade=grade,
        name=name,
    )
    return class_obj


def _letter_for_index(index: int) -> str:
    return chr(65 + index)


@transaction.atomic
def auto_generate_classes(school_id: int) -> list[Class]:
    from students.models import Student

    MAX_PER_CLASS = 40
    school = School.objects.get(id=school_id)
    students = (
        Student.objects.filter(school_id=school_id, grade__isnull=False)
        .select_related("grade")
        .order_by("grade__level", "full_name")
    )

    by_grade: dict[int, list[Student]] = {}
    for s in students:
        by_grade.setdefault(s.grade.level, []).append(s)

    created: list[Class] = []
    for grade_level, grade_students in sorted(by_grade.items()):
        grade = grade_students[0].grade
        for i in range(0, len(grade_students), MAX_PER_CLASS):
            chunk = grade_students[i : i + MAX_PER_CLASS]
            letter = _letter_for_index(i // MAX_PER_CLASS)
            class_obj = get_or_create_class(school, grade, letter)
            created.append(class_obj)
            for student in chunk:
                student.class_fk = class_obj
            Student.objects.bulk_update(
                chunk, ["class_fk"]
            )

    return created
