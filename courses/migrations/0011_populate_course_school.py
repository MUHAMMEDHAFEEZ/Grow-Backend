from django.db import migrations


def populate_course_school(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    for course in Course.objects.filter(school__isnull=True).select_related("grade__school"):
        if course.grade_id and course.grade and course.grade.school_id:
            course.school_id = course.grade.school_id
            course.save(update_fields=["school"])


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0010_course_school'),
    ]

    operations = [
        migrations.RunPython(populate_course_school, migrations.RunPython.noop),
    ]
