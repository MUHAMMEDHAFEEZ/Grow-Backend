from django.utils import timezone
from . import selectors


LEVEL_THRESHOLDS = [
    (0, 1),
    (101, 2),
    (301, 3),
    (601, 4),
    (1001, 5),
]


def calculate_level(total_xp):
    """Calculate level from XP thresholds."""
    level = 1
    for threshold, lev in LEVEL_THRESHOLDS:
        if total_xp >= threshold:
            level = lev
    return level


def get_level_progress(total_xp):
    """Calculate progress within current level."""
    level = calculate_level(total_xp)

    if level >= 5:
        return {'current': 1000, 'next': None, 'percentage': 100}

    current_threshold = LEVEL_THRESHOLDS[level - 1][0]
    next_threshold = LEVEL_THRESHOLDS[level][0]

    xp_in_level = total_xp - current_threshold
    xp_needed = next_threshold - current_threshold

    percentage = int((xp_in_level / xp_needed) * 100) if xp_needed > 0 else 100

    return {
        'current': total_xp,
        'next': next_threshold,
        'percentage': min(percentage, 100),
    }


def get_welcome_section(student):
    """Welcome section with student name."""
    today = timezone.now().date()

    completed_today = 0
    total_today = 0

    return {
        'name': student.full_name,
        'daily_progress': {
            'completed': completed_today,
            'total': total_today,
            'percentage': 0,
        }
    }


def get_xp_section(student):
    """XP system section."""
    xp_data = selectors.get_student_xp(student)

    total = xp_data['total']
    today = xp_data['today']
    yesterday = xp_data['yesterday']

    level = calculate_level(total)
    level_progress = get_level_progress(total)

    daily_change = 0
    if yesterday > 0:
        daily_change = int(((today - yesterday) / yesterday) * 100)

    return {
        'total': total,
        'today': today,
        'yesterday': yesterday,
        'daily_change': daily_change,
        'level': level,
        'level_progress': level_progress,
    }


def get_daily_mastery_section(student):
    """Daily mastery progress section."""
    tasks = selectors.get_student_tasks_today(student)

    total = len(tasks)
    completed = sum(1 for t in tasks if t['status'] == 'submitted')

    percentage = int((completed / total) * 100) if total > 0 else 0

    return {
        'completed': completed,
        'total': total,
        'remaining': total - completed,
        'percentage': percentage,
    }


def get_streak_section(student):
    """Daily streak section."""
    streak = selectors.get_student_streak(student)

    return {'count': streak}


def get_leaderboard_section(student):
    """Leaderboard section."""
    top_students = selectors.get_leaderboard(limit=10)
    rank = selectors.get_student_rank(student)

    leaderboard = []
    for i, s in enumerate(top_students):
        leaderboard.append({
            'rank': i + 1,
            'name': s.get('student__student_profile__full_name', 'Unknown'),
            'xp': s.get('total_xp', 0),
        })

    return {
        'top_10': leaderboard,
        'rank': rank,
    }


def get_today_tasks_section(student):
    """Today's tasks section."""
    tasks = selectors.get_student_tasks_today(student)

    return {'tasks': tasks}


def get_weekly_progress_section(student):
    """Weekly progress section."""
    weekly = selectors.get_student_weekly_hours(student)

    status = 'on_track'
    if weekly['percentage'] > 100:
        status = 'ahead'
    elif weekly['percentage'] < 50:
        status = 'behind'

    return {
        'hours': weekly['total_hours'],
        'goal': weekly['goal_hours'],
        'percentage': weekly['percentage'],
        'status': status,
    }


def get_upcoming_session_section(student):
    """Upcoming session section."""
    session = selectors.get_upcoming_session(student)

    if session:
        return session

    return None


def get_student_dashboard(student):
    """
    Get complete student dashboard.

    Returns all 8 sections of the dashboard.
    """
    return {
        'welcome': get_welcome_section(student),
        'xp_system': get_xp_section(student),
        'daily_mastery': get_daily_mastery_section(student),
        'daily_streak': get_streak_section(student),
        'leaderboard': get_leaderboard_section(student),
        'today_tasks': get_today_tasks_section(student),
        'weekly_progress': get_weekly_progress_section(student),
        'upcoming_session': get_upcoming_session_section(student),
    }