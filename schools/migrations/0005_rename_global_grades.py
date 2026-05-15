from django.db import migrations


LEVEL_STAGES = {
    1: ("Grade 1", "primary"),
    2: ("Grade 2", "primary"),
    3: ("Grade 3", "primary"),
    4: ("Grade 4", "primary"),
    5: ("Grade 5", "primary"),
    6: ("Grade 6", "primary"),
    7: ("Grade 7", "secondary"),
    8: ("Grade 8", "secondary"),
    9: ("Grade 9", "secondary"),
    10: ("Grade 10", "secondary"),
    11: ("Grade 11", "secondary"),
    12: ("Grade 12", "secondary"),
}


def rename_global_grades(apps, schema_editor):
    Grade = apps.get_model("schools", "Grade")
    for level, (name, stage) in LEVEL_STAGES.items():
        Grade.objects.filter(level=level, school__isnull=True).update(
            name=name, stage=stage
        )


def reverse_rename(apps, schema_editor):
    Grade = apps.get_model("schools", "Grade")
    Grade.objects.filter(
        school__isnull=True, level__gte=1, level__lte=12
    ).update(name="", stage="")


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0004_grade_school_registrationcode"),
    ]

    operations = [
        migrations.RunPython(rename_global_grades, reverse_rename),
    ]
