from django.core.management.base import BaseCommand

from dashboard.services import generate_insights


class Command(BaseCommand):
    help = "Generate dashboard insights: overcrowded classes, performance drops, at-risk students"

    def handle(self, *args, **options):
        self.stdout.write("Generating dashboard insights...")
        results = generate_insights()
        if results:
            for r in results:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [{r['severity']}] {r['title']} ({r['type']})"
                    )
                )
            self.stdout.write(
                self.style.SUCCESS(f"\nCreated {len(results)} new insight(s)")
            )
        else:
            self.stdout.write(self.style.WARNING("No new insights generated"))
