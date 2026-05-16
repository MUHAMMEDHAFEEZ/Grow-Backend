from django.db import migrations


SCHOOL_ADMIN_MAP = {
    "ELOBOUR": "admin@elobour.edu",
    "ELFOUAD": "admin@elfouad.edu",
    "ELSHOBAN": "admin@elshoban.edu",
}


def populate_school_admin(apps, schema_editor):
    schools_School = apps.get_model("schools", "School")
    User = apps.get_model("accounts", "User")
    for name, email in SCHOOL_ADMIN_MAP.items():
        school = schools_School.objects.filter(name__iexact=name).first()
        admin = User.objects.filter(email=email, role="school_admin").first()
        if school and admin:
            school.admin = admin
            school.save(update_fields=["admin"])


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0006_school_admin_class'),
    ]

    operations = [
        migrations.RunPython(populate_school_admin, migrations.RunPython.noop),
    ]
