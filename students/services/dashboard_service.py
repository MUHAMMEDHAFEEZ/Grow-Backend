from students.services.daily_master_service import get_or_create_daily_log
from students.services.leaderboard_service import get_leaderboard
from students.services.streak_service import calculate_streak
from students.services.task_service import get_todays_tasks
from students.services.xp_service import get_total_xp


def get_dashboard(student):
    total_xp = get_total_xp(student)
    daily_streak = calculate_streak(student)
    todays_tasks = get_todays_tasks(student)
    daily_master = get_or_create_daily_log(student)
    leaderboard = get_leaderboard(student)

    completed = len([t for t in todays_tasks if t["status"] == "submitted"])
    total = len(todays_tasks)

    return {
        "total_xp": total_xp,
        "daily_streak": daily_streak,
        "todays_tasks": todays_tasks,
        "daily_master": {
            "tasks_total": daily_master.tasks_total,
            "tasks_completed": daily_master.tasks_completed,
            "completion_percentage": daily_master.completion_percentage,
            "level": daily_master.level,
        },
        "leaderboard": leaderboard,
    }
