from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from xp.models import XPTransaction
from study_sessions.models import StudySession
from submissions.models import Submission
from assignments.models import Assignment


def get_student_xp(student):
    """Get total XP and daily XP change for a student."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = (today_start - timezone.timedelta(days=1))

    total_xp = XPTransaction.objects.filter(
        student=student
    ).aggregate(total=Coalesce(Sum('xp_amount'), 0))['total'] or 0

    today_xp = XPTransaction.objects.filter(
        student=student,
        created_at__gte=today_start
    ).aggregate(total=Coalesce(Sum('xp_amount'), 0))['total'] or 0

    yesterday_xp = XPTransaction.objects.filter(
        student=student,
        created_at__gte=yesterday_start,
        created_at__lt=today_start
    ).aggregate(total=Coalesce(Sum('xp_amount'), 0))['total'] or 0

    return {
        'total': total_xp,
        'today': today_xp,
        'yesterday': yesterday_xp,
    }


def get_student_streak(student):
    """Calculate consecutive days of activity."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    xp_dates = XPTransaction.objects.filter(
        student=student
    ).dates('created_at', 'day').distinct()

    session_dates = StudySession.objects.filter(
        student=student
    ).dates('started_at', 'day').distinct()

    all_activity_dates = set(
        list(xp_dates.values_list('created_at', flat=True)) +
        list(session_dates.values_list('started_at', flat=True))
    )

    if not all_activity_dates:
        return 0

    sorted_dates = sorted(all_activity_dates, reverse=True)
    streak = 0
    check_date = today_start.date() if today_start.date() in sorted_dates else None

    if check_date is None:
        yesterday = (today_start - timezone.timedelta(days=1)).date()
        if yesterday in sorted_dates:
            check_date = yesterday
        else:
            return 0

    current_date = check_date
    for date in sorted_dates:
        if date == current_date:
            streak += 1
            current_date -= timezone.timedelta(days=1)
        elif date < current_date:
            break

    return streak


def get_student_tasks_today(student):
    """Get assignments due today with submission status."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timezone.timedelta(days=1)

    grade = getattr(getattr(student, 'student_profile', None), 'grade', None)

    assignments = Assignment.objects.filter(
        due_date__gte=today_start,
        due_date__lt=today_end,
        course__grade=grade
    ).select_related('course')

    tasks = []
    for assignment in assignments:
        submission = Submission.objects.filter(
            student=student,
            assignment=assignment
        ).first()

        tasks.append({
            'id': assignment.id,
            'title': assignment.title,
            'subject': assignment.course.name if assignment.course else None,
            'due_date': assignment.due_date,
            'status': submission.status if submission else 'pending',
        })

    return tasks


def get_student_weekly_hours(student):
    """Calculate weekly study hours."""
    now = timezone.now()
    week_start = now - timezone.timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    sessions = StudySession.objects.filter(
        student=student,
        started_at__gte=week_start
    )

    total_seconds = sessions.aggregate(
        total=Coalesce(Sum('duration'), 0)
    )['total'] or 0

    total_hours = total_seconds / 3600

    return {
        'total_hours': round(total_hours, 2),
        'goal_hours': 10,
        'percentage': min(int((total_hours / 10) * 100), 100),
    }


def get_leaderboard(limit=10):
    """Get top students by XP."""

    top_students = XPTransaction.objects.values(
        'student__id',
        'student__student_profile__full_name'
    ).annotate(
        total_xp=Sum('xp_amount')
    ).order_by('-total_xp')[:limit]

    return list(top_students)


def get_student_rank(student):
    """Get student's rank by XP."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("""
            WITH xp_ranks AS (
                SELECT 
                    student_id,
                    SUM(xp_amount) as total_xp,
                    ROW_NUMBER() OVER (ORDER BY SUM(xp_amount) DESC) as rank
                FROM xp_xptransaction
                WHERE student_id = %s
                GROUP BY student_id
            )
            SELECT rank FROM xp_ranks WHERE student_id = %s
        """, [student.id, student.id])

        result = cursor.fetchone()
        if result:
            return result[0]

    student_xp = XPTransaction.objects.filter(
        student=student
    ).aggregate(total=Coalesce(Sum('xp_amount'), 0))['total'] or 0

    if student_xp == 0:
        return 0

    higher_count = XPTransaction.objects.values('student').annotate(
        total_xp=Sum('xp_amount')
    ).filter(total_xp__gt=student_xp).count()

    return higher_count + 1


def get_upcoming_session(student):
    """Get upcoming study session."""
    now = timezone.now()

    session = StudySession.objects.filter(
        student=student,
        started_at__gt=now
    ).order_by('started_at').first()

    if session:
        end_time = session.started_at + timezone.timedelta(seconds=session.duration)
        return {
            'title': 'Study Session',
            'scheduled_at': session.started_at,
            'time_range': f"{session.started_at.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
        }

    return None


# ── Base Selectors (Student Role Backend) ──────────────────────────────────────


def get_courses_for_student(student, filter_status="all"):
    from courses.models import Course, CourseProgress

    profile = getattr(student, 'student_profile', None)
    if profile is None or profile.grade is None or profile.school is None:
        return []

    courses = Course.objects.filter(
        school=profile.school,
        grade__level=profile.grade.level,
        is_published=True,
    ).prefetch_related("lessons")

    if filter_status == "inprogress":
        completed_ids = CourseProgress.objects.filter(
            student=student, completion_status="completed"
        ).values_list("course_id", flat=True)
        courses = courses.exclude(id__in=completed_ids)
    elif filter_status == "completed":
        completed_ids = CourseProgress.objects.filter(
            student=student, completion_status="completed"
        ).values_list("course_id", flat=True)
        courses = courses.filter(id__in=completed_ids)

    result = []
    for course in courses:
        progress = CourseProgress.objects.filter(student=student, course=course).first()
        result.append({
            "id": course.id,
            "name": course.title,
            "completion_percentage": float(progress.progress_percentage) if progress else 0.0,
            "status": progress.completion_status if progress else "not_started",
        })
    return result


def get_course_detail(course_id, student):
    from courses.models import Course, Lesson, QuizAttempt
    from quizzes.models import Quiz
    from assignments.models import Assignment
    from students.models import LessonCompletion

    course = Course.objects.prefetch_related("lessons").get(id=course_id)
    lessons = Lesson.objects.filter(course=course).order_by("order", "created_at")
    quizzes = Quiz.objects.filter(course=course)
    assignments = Assignment.objects.filter(course=course)

    attempted_quiz_ids = set(
        QuizAttempt.objects.filter(
            student=student, quiz__in=quizzes
        ).values_list("quiz_id", flat=True)
    )

    lesson_data = []
    for lesson in lessons:
        is_completed = LessonCompletion.objects.filter(student=student, lesson=lesson).exists()
        lesson_data.append({
            "id": lesson.id,
            "title": lesson.title,
            "content": lesson.content,
            "video_url": lesson.video_url,
            "video_file": lesson.video_file.url if lesson.video_file else None,
            "pdf_file": lesson.pdf_file.url if lesson.pdf_file else None,
            "resources": lesson.resources.url if lesson.resources else None,
            "xp_reward": lesson.xp_reward,
            "bonus_xp": lesson.bonus_xp,
            "status": lesson.status,
            "order": lesson.order,
            "is_completed": is_completed,
        })

    total_lessons = lessons.count()
    completed_lessons = sum(1 for _ in lesson_data if _["is_completed"])
    completion_pct = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

    quiz_data = []
    for q in quizzes:
        quiz_data.append({
            "id": q.id,
            "title": q.title,
            "is_completed": q.id in attempted_quiz_ids,
        })

    return {
        "course_name": course.title,
        "completion_percentage": round(completion_pct, 2),
        "lessons": lesson_data,
        "quizzes": quiz_data,
        "assignments": list(assignments.values("id", "title", "due_date")),
    }


def get_quiz_with_questions(quiz_id, student):
    from courses.models import Quiz, QuizAttempt

    quiz = Quiz.objects.prefetch_related("questions").get(id=quiz_id)
    has_attempt = QuizAttempt.objects.filter(student=student, quiz=quiz).exists()

    return {
        "id": quiz.id,
        "title": quiz.title,
        "questions": list(quiz.questions.values("id", "text", "options")),
        "has_attempt": has_attempt,
    }


def get_assignment_detail(assignment_id, student):
    from assignments.models import Assignment

    assignment = Assignment.objects.select_related("course").get(id=assignment_id)
    submission = Submission.objects.filter(student=student, assignment=assignment).first()

    return {
        "id": assignment.id,
        "title": assignment.title,
        "deadline": assignment.due_date,
        "teacher_file_url": None,
        "submission_status": submission.status if submission else "pending",
        "is_graded": submission.is_graded if submission else False,
        "score": submission.raw_score if submission and submission.is_graded else None,
        "feedback": submission.feedback if submission and submission.is_graded else None,
        "xp_awarded": submission.xp_awarded if submission and submission.is_graded else None,
    }


def get_past_due_items(student):
    from assignments.models import Assignment
    from courses.models import Quiz, QuizAttempt

    grade = getattr(getattr(student, 'student_profile', None), 'grade', None)

    now = timezone.now()

    assignments = Assignment.objects.filter(
        course__grade=grade,
        due_date__lt=now,
    ).exclude(
        submissions__student=student,
    ).select_related("course")

    past_due = [
        {
            "id": a.id,
            "title": a.title,
            "type": "assignment",
            "deadline": a.due_date,
        }
        for a in assignments
    ]

    attempted_quiz_ids = set(
        QuizAttempt.objects.filter(student=student).values_list("quiz_id", flat=True)
    )
    quizzes = Quiz.objects.filter(
        course__grade=grade,
        end_time__lt=now,
    ).exclude(id__in=attempted_quiz_ids)

    for q in quizzes:
        past_due.append({
            "id": q.id,
            "title": q.title,
            "type": "quiz",
            "deadline": q.end_time,
        })

    return past_due


def get_todays_missions(student):
    from assignments.models import Assignment
    from courses.models import Quiz, QuizAttempt

    grade = getattr(getattr(student, 'student_profile', None), 'grade', None)

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timezone.timedelta(days=1)

    assignments = Assignment.objects.filter(
        course__grade=grade,
        due_date__gte=today_start,
        due_date__lt=today_end,
    ).select_related("course")

    result = []
    for a in assignments:
        submission = Submission.objects.filter(student=student, assignment=a).first()
        result.append({
            "id": a.id,
            "title": a.title,
            "type": "assignment",
            "xp_reward": a.xp_reward or 50,
            "is_completed": submission is not None,
        })

    attempted_quiz_ids = set(
        QuizAttempt.objects.filter(student=student).values_list("quiz_id", flat=True)
    )
    quizzes = Quiz.objects.filter(
        course__grade=grade,
        start_time__gte=today_start,
        start_time__lt=today_end,
    )

    for q in quizzes:
        result.append({
            "id": q.id,
            "title": q.title,
            "type": "quiz",
            "xp_reward": q.xp_reward or 50,
            "is_completed": q.id in attempted_quiz_ids,
        })

    return result


def get_student_settings(student):
    from courses.models import StudentCourse

    profile = getattr(student, 'student_profile', None)

    total_xp = XPTransaction.objects.filter(student=student).aggregate(
        total=Coalesce(Sum("xp_amount"), 0)
    )["total"] or 0

    courses_count = StudentCourse.objects.filter(student=student).count()

    return {
        "full_name": profile.full_name if profile else None,
        "email": student.email,
        "student_id": profile.student_id if profile else None,
        "school": profile.school.name if profile and profile.school else None,
        "grade": profile.grade.name if profile and profile.grade else None,
        "total_xp": total_xp,
        "courses_count": courses_count,
    }


def get_notifications(student, page=1, page_size=20):
    from students.models import StudentNotification

    queryset = StudentNotification.objects.filter(student=student)
    offset = (page - 1) * page_size
    return list(queryset.order_by("-created_at")[offset : offset + page_size])


def get_students_by_school(school_id: int):
    from students.models import Student

    return Student.objects.filter(school_id=school_id, user__isnull=False).select_related("user", "grade").order_by("-created_at")