import secrets
import string

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from schools.models import Grade, RegistrationCode, School as EduSchool

User = get_user_model()

SCHOOLS = [
    {"name": "ELOBOUR", "code": "ELB", "admin_email": "admin@elobour.edu", "admin_pass": "school1pass"},
    {"name": "ELFOUAD", "code": "ELF", "admin_email": "admin@elfouad.edu", "admin_pass": "school2pass"},
    {"name": "ELSHOBAN", "code": "ELS", "admin_email": "admin@elshoban.edu", "admin_pass": "school3pass"},
]

STUDENT_CODES_PER_GRADE = 10
TEACHER_CODES_PER_SCHOOL = 10


def _generate_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _ensure_unique_code(existing: set, length: int = 8) -> str:
    while True:
        code = _generate_code(length)
        if code not in existing:
            existing.add(code)
            return code


class Command(BaseCommand):
    help = "Seed schools, grades, registration codes, and admin accounts."

    def handle(self, *args, **options):
        self._seed_edu_schools()
        self.stdout.write(self.style.SUCCESS("Seeding complete."))

    @transaction.atomic
    def _seed_edu_schools(self):
        all_codes: set[str] = set()

        for school_data in SCHOOLS:
            edu_school, created = EduSchool.objects.get_or_create(
                school_code=school_data["code"],
                defaults={
                    "name": school_data["name"],
                    "school_type": "arabic",
                },
            )
            if created:
                self.stdout.write(f"  Created school: {edu_school.name}")
            else:
                self.stdout.write(f"  Found existing school: {edu_school.name}")

            self._seed_grades(edu_school)
            self._seed_student_codes(edu_school, all_codes)
            self._seed_teacher_codes(edu_school, all_codes)
            self._seed_admin_account(school_data)

    def _seed_grades(self, edu_school):
        for level in range(1, 13):
            stage = "primary" if level <= 6 else "secondary"
            Grade.objects.get_or_create(
                name=f"Grade {level}",
                level=level,
                stage=stage,
                school=edu_school,
            )
        count = Grade.objects.filter(school=edu_school).count()
        self.stdout.write(f"    Grades: {count}")

    def _seed_student_codes(self, edu_school, all_codes):
        grades = Grade.objects.filter(school=edu_school)
        created = 0
        for grade in grades:
            existing = RegistrationCode.objects.filter(
                school=edu_school, grade=grade, code_type="student"
            ).count()
            needed = STUDENT_CODES_PER_GRADE - existing
            for _ in range(needed):
                code_str = _ensure_unique_code(all_codes)
                RegistrationCode.objects.create(
                    code=code_str,
                    school=edu_school,
                    grade=grade,
                    code_type="student",
                )
                created += 1
        if created:
            self.stdout.write(f"    Student codes created: {created}")

    def _seed_teacher_codes(self, edu_school, all_codes):
        existing = RegistrationCode.objects.filter(
            school=edu_school, code_type="teacher"
        ).count()
        needed = TEACHER_CODES_PER_SCHOOL - existing
        for _ in range(needed):
            code_str = _ensure_unique_code(all_codes)
            RegistrationCode.objects.create(
                code=code_str,
                school=edu_school,
                code_type="teacher",
            )
        if needed:
            self.stdout.write(f"    Teacher codes created: {needed}")

    def _seed_admin_account(self, school_data):
        username = school_data["name"].lower().replace(" ", "_") + "_admin"
        user, created = User.objects.get_or_create(
            email=school_data["admin_email"],
            defaults={
                "username": username,
                "role": User.Role.SCHOOL_ADMIN,
            },
        )
        if created:
            user.set_password(school_data["admin_pass"])
            user.save(update_fields=["password"])
            self.stdout.write(f"    Admin account created: {school_data['admin_email']}")
        else:
            self.stdout.write(f"    Admin account exists: {school_data['admin_email']}")
