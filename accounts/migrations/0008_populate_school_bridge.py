from django.db import migrations


def populate_school_bridge(apps, schema_editor):
    accounts_School = apps.get_model("accounts", "School")
    schools_School = apps.get_model("schools", "School")
    for a_school in accounts_School.objects.filter(schools_school__isnull=True):
        match = schools_School.objects.filter(name__iexact=a_school.name).first()
        if match:
            a_school.schools_school = match
            a_school.save(update_fields=["schools_school"])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_school_schools_school'),
    ]

    operations = [
        migrations.RunPython(populate_school_bridge, migrations.RunPython.noop),
    ]
