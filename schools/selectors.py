from django.db.models import Min

from schools.models import Grade


def get_grades_for_school(school_id: int | None = None):
    qs = Grade.objects.all()
    if school_id is not None:
        qs = qs.filter(school_id=school_id)
    else:
        qs = qs.filter(school__isnull=True)

    ids = (
        qs.values("level")
        .annotate(min_id=Min("id"))
        .values_list("min_id", flat=True)
    )
    return Grade.objects.filter(id__in=ids).order_by("level")
