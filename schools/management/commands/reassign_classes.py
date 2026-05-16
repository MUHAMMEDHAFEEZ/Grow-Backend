from django.core.management.base import BaseCommand

from schools.models import School
from schools.services.class_service import auto_generate_classes


class Command(BaseCommand):
    help = "Auto-generate classes for all schools (or a specific school) based on current student distribution."

    def add_arguments(self, parser):
        parser.add_argument(
            "--school",
            type=int,
            help="School ID to regenerate classes for (default: all schools).",
        )

    def handle(self, *args, **options):
        school_id = options.get("school")
        if school_id:
            schools = School.objects.filter(id=school_id)
        else:
            schools = School.objects.all()

        for school in schools:
            created = auto_generate_classes(school.id)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{school.name}: {len(created)} classes, "
                    f"students assigned via idempotent generation."
                )
            )
