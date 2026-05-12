from django.utils import timezone

from students.models import DailyMasterLog


def get_or_create_daily_log(student):
    today = timezone.now().date()
    log, created = DailyMasterLog.objects.get_or_create(
        student=student,
        date=today,
        defaults={"tasks_total": 0, "tasks_completed": 0, "level": 1},
    )
    return log


def update_completion(student):
    log = get_or_create_daily_log(student)

    if log.tasks_total > 0 and log.tasks_completed >= log.tasks_total:
        log.level += 1
        log.tasks_completed = 0
        log.tasks_total = 0
        log.save(update_fields=["level", "tasks_completed", "tasks_total"])
        return log

    return log
