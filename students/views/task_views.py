from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from assignments.models import Assignment
from core.permissions import IsStudent
from students.selectors import get_past_due_items, get_todays_missions
from students.serializers.task_serializers import TasksResponseSerializer
from students.services.daily_master_service import get_or_create_daily_log
from students.services.streak_service import calculate_streak
from students.services.xp_service import get_total_xp
from submissions.models import Submission
from xp.models import XPTransaction


@extend_schema(
    tags=["Student Tasks"],
    summary="Tasks overview",
    description="Get past-due items, today's missions, and summary bar.",
    responses={200: TasksResponseSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStudent])
def student_tasks_view(request):
    student = request.user

    past_due = get_past_due_items(student)
    todays_missions = get_todays_missions(student)

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    today_xp = XPTransaction.objects.filter(
        student=student, created_at__gte=today_start
    ).aggregate(total=Coalesce(Sum("xp_amount"), 0))["total"] or 0

    streak = calculate_streak(student)
    daily_master = get_or_create_daily_log(student)

    data = {
        "past_due": [
            {
                "title": item["title"],
                "subject": None,
                "type": item["type"],
                "deadline": item["deadline"],
                "xp_reward": 50,
                "status": "past_due",
            }
            for item in past_due
        ],
        "todays_missions": [
            {
                "title": item["title"],
                "subject": None,
                "type": item["type"],
                "xp_reward": item.get("xp_reward", 50),
                "is_completed": item.get("is_completed", False),
            }
            for item in todays_missions
        ],
        "summary_bar": {
            "current_streak": streak,
            "total_xp_today": today_xp,
            "daily_master_percentage": daily_master.completion_percentage,
        },
    }

    serializer = TasksResponseSerializer(data)
    return Response(serializer.data)
