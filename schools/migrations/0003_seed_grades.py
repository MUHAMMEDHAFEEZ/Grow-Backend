from django.db import migrations


def seed_grades(apps, schema_editor):
    Grade = apps.get_model("schools", "Grade")
    grades = [
        (1, "الأول الابتدائي", "Primary"),
        (2, "الثاني الابتدائي", "Primary"),
        (3, "الثالث الابتدائي", "Primary"),
        (4, "الرابع الابتدائي", "Primary"),
        (5, "الخامس الابتدائي", "Primary"),
        (6, "السادس الابتدائي", "Primary"),
        (7, "الأول الإعدادي", "Preparatory"),
        (8, "الثاني الإعدادي", "Preparatory"),
        (9, "الثالث الإعدادي", "Preparatory"),
        (10, "الأول الثانوي", "Secondary"),
        (11, "الثاني الثانوي", "Secondary"),
        (12, "الثالث الثانوي", "Secondary"),
    ]
    for level, name, stage in grades:
        Grade.objects.get_or_create(level=level, defaults={"name": name, "stage": stage})


def reverse_seed(apps, schema_editor):
    Grade = apps.get_model("schools", "Grade")
    Grade.objects.filter(level__range=(1, 12)).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0002_grade_subject_course"),
    ]

    operations = [
        migrations.RunPython(seed_grades, reverse_seed),
    ]
