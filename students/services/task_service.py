from django.utils import timezone

from assignments.models import Assignment
from submissions.models import Submission


def get_todays_tasks(student):
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timezone.timedelta(days=1)

    tasks = []

    assignments = Assignment.objects.filter(
        course__grade=student.grade,
        due_date__gte=today_start,
        due_date__lt=today_end,
    ).select_related("course")

    for a in assignments:
        submission = Submission.objects.filter(student=student, assignment=a).first()
        tasks.append({
            "title": a.title,
            "subject": a.course.title if a.course else None,
            "type": "assignment",
            "time_remaining": None,
            "xp_reward": 50,
            "status": submission.status if submission else "pending",
        })

    return tasks
