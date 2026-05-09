"""
courses/services.py — Business logic for courses, enrollments, and lessons.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone

from attendance.domain import AttendanceResult, LessonAttendanceSummary
from attendance.services import calculate_attendance_status, upsert_attendance
from core.events import EventBus, Events
from core.exceptions import Conflict, NotFound, PermissionDenied, RateLimitExceeded

from .models import Course, CourseProgress, Lesson, LessonActivity, Quiz, QuizAttempt, StudentCourse
from .selectors import (
    get_attempt_count,
    get_enrolled_student_ids,
    get_lesson_or_404,
    is_student_enrolled_in_course,
)

User = get_user_model()


def create_course(*, teacher: User, title: str, description: str = "") -> Course:
    if not teacher.is_teacher:
        raise PermissionDenied("Only teachers can create courses.")
    course = Course.objects.create(
        teacher=teacher, title=title, description=description
    )
    return course


def update_course(*, course_id: int, teacher: User, **fields) -> Course:
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise NotFound("Course not found.")
    if course.teacher_id != teacher.pk:
        raise PermissionDenied("You do not own this course.")
    for key, value in fields.items():
        setattr(course, key, value)
    course.save()
    return course


def delete_course(*, course_id: int, teacher: User) -> None:
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise NotFound("Course not found.")
    if course.teacher_id != teacher.pk:
        raise PermissionDenied("You do not own this course.")
    course.delete()


def enroll_student(*, course_id: int, student: User) -> StudentCourse:
    """Lazy enrollment — upserts StudentCourse on first interaction."""
    if not student.is_student:
        raise PermissionDenied("Only students can enroll.")
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise NotFound("Course not found.")
    sc, created = StudentCourse.objects.get_or_create(
        course=course,
        student=student,
        defaults={"is_active": True},
    )
    if created:
        EventBus.publish(
            Events.COURSE_OPENED,
            {
                "student_id": student.pk,
                "course_id": course.pk,
                "course_title": course.title,
                "timestamp": str(sc.enrolled_at.isoformat()),
            },
        )
    return sc


def set_course_grade(*, course_id: int, teacher: User, grade_id: int) -> Course:
    """Assign a grade to a course. Teacher must own the course."""
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise NotFound("Course not found.")
    if course.teacher_id != teacher.pk:
        raise PermissionDenied("You do not own this course.")
    from schools.models import Grade
    try:
        grade = Grade.objects.get(pk=grade_id)
    except Grade.DoesNotExist:
        raise NotFound("Grade not found.")
    course.grade = grade
    course.save()
    return course


def create_lesson(
    *,
    course_id: int,
    teacher: User,
    title: str,
    content: str,
    order: int = 0,
    start_time=None,
    end_time=None,
) -> Lesson:
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise NotFound("Course not found.")
    if course.teacher_id != teacher.pk:
        raise PermissionDenied("You do not own this course.")
    lesson = Lesson.objects.create(
        course=course,
        title=title,
        content=content,
        order=order,
        start_time=start_time,
        end_time=end_time,
    )
    EventBus.publish(
        Events.LESSON_CREATED,
        {
            "lesson_id": lesson.pk,
            "course_id": course.pk,
            "course_title": course.title,
            "lesson_title": lesson.title,
        },
    )
    return lesson


def join_lesson(*, lesson_id: int, student: User) -> AttendanceResult:
    """
    Student joins a lesson and receives automatic attendance status.

    Business rules:
    - Server time is used for all calculations
    - Status calculation: present (within 10 min), late (>10 min), absent (after end)
    - Rejects early joins (before start_time)
    - Validates enrollment
    - Uses upsert to prevent duplicates
    """
    lesson = get_lesson_or_404(lesson_id)

    if not is_student_enrolled_in_course(student, lesson.course_id):
        from core.exceptions import PermissionDenied as PD

        raise PD("You are not enrolled in this course.")

    if not lesson.start_time or not lesson.end_time:
        from core.exceptions import ValidationError as VE

        raise VE("This lesson does not have a scheduled time.")

    current_time = timezone.now()
    status = calculate_attendance_status(
        current_time=current_time,
        start_time=lesson.start_time,
        end_time=lesson.end_time,
    )

    result = upsert_attendance(
        student=student,
        course=lesson.course,
        date=lesson.start_time.date(),
        status=status,
        lesson_id=lesson_id,
    )

    EventBus.publish(
        "lesson_joined",
        {
            "lesson_id": lesson_id,
            "student_id": student.pk,
            "status": status,
            "course_id": lesson.course_id,
        },
    )

    return result


# ----- Course Progress -----

_MILESTONES = {25, 50, 75, 100}


def update_progress(
    *,
    student: User,
    course: Course,
    progress_delta: float | None = None,
    study_time_delta: int | None = None,
) -> CourseProgress:
    """
    Update or create a CourseProgress record for a student + course.

    - Rate-limited: only persists if >60s since last update (unless milestone).
    - Transitions not_started → in_progress on first interaction.
    - Transitions in_progress → completed at 100%.
    - Publishes PROGRESS_MILESTONE_REACHED at 25/50/75/100.
    """
    progress, created = CourseProgress.objects.get_or_create(
        student=student,
        course=course,
        defaults={"completion_status": CourseProgress.CompletionStatus.IN_PROGRESS},
    )

    # Rate limit: skip if updated within last 60 seconds (unless milestone)
    now = timezone.now()
    if (
        progress.last_activity
        and (now - progress.last_activity).total_seconds() < 60
        and progress_delta is not None
    ):
        # Still update last_activity if a lesson was just completed
        if progress_delta is not None and progress_delta <= 0:
            progress.last_activity = now
            progress.save(update_fields=["last_activity"])
            return progress
        return progress

    # State transition: not_started → in_progress
    if created or progress.completion_status == CourseProgress.CompletionStatus.NOT_STARTED:
        progress.completion_status = CourseProgress.CompletionStatus.IN_PROGRESS

    # Apply deltas
    if progress_delta is not None and progress_delta > 0:
        new_pct = float(progress.progress_percentage) + progress_delta
        progress.progress_percentage = min(new_pct, 100.00)

    if study_time_delta is not None and study_time_delta > 0:
        progress.study_time_seconds += study_time_delta

    progress.last_activity = now

    # Milestone check before potential completion transition
    old_pct = float(progress.progress_percentage) - (progress_delta or 0)
    for ms in sorted(_MILESTONES):
        if old_pct < ms <= float(progress.progress_percentage):
            EventBus.publish(
                Events.PROGRESS_MILESTONE_REACHED,
                {
                    "student_id": student.pk,
                    "course_id": course.pk,
                    "milestone_percentage": ms,
                    "timestamp": now.isoformat(),
                },
            )

    # Completion check
    if float(progress.progress_percentage) >= 100.00:
        progress.completion_status = CourseProgress.CompletionStatus.COMPLETED

    progress.save()
    return progress


# ----- Quiz Attempts -----


def submit_quiz_attempt(
    *, student: User, quiz_id: int, score: float
) -> QuizAttempt:
    """
    Submit a quiz attempt.

    - Auto-increments attempt_number.
    - Rate-limited: max 10 attempts per 5 minutes per (student, quiz).
    - Publishes Events.QUIZ_SUBMITTED.
    """
    try:
        quiz = Quiz.objects.select_related("course").get(pk=quiz_id)
    except Quiz.DoesNotExist:
        raise NotFound("Quiz not found.")

    if not is_student_enrolled_in_course(student, quiz.course_id):
        raise PermissionDenied("You are not enrolled in this course.")

    # Rate limit: max 10 attempts in last 5 minutes
    from django.utils import timezone as tz
    five_min_ago = tz.now() - tz.timedelta(minutes=5)
    recent_count = QuizAttempt.objects.filter(
        student=student, quiz=quiz, submitted_at__gte=five_min_ago
    ).count()
    if recent_count >= 10:
        raise RateLimitExceeded(
            "Maximum 10 quiz attempts per 5 minutes."
        )

    attempt_number = get_attempt_count(student, quiz) + 1
    attempt = QuizAttempt.objects.create(
        student=student,
        quiz=quiz,
        score=score,
        attempt_number=attempt_number,
    )

    EventBus.publish(
        Events.QUIZ_SUBMITTED,
        {
            "student_id": student.pk,
            "quiz_id": quiz_id,
            "course_id": quiz.course_id,
            "score": float(score),
            "attempt_number": attempt_number,
            "timestamp": attempt.submitted_at.isoformat(),
        },
    )

    return attempt


def create_quiz(
    *, course_id: int, teacher: User, title: str, max_score: float,
    lesson_id: int | None = None,
) -> Quiz:
    """Teacher creates a quiz for a course they own."""
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise NotFound("Course not found.")
    if course.teacher_id != teacher.pk:
        raise PermissionDenied("You do not own this course.")
    quiz = Quiz.objects.create(
        course=course,
        lesson_id=lesson_id,
        title=title,
        max_score=max_score,
    )
    EventBus.publish(
        Events.QUIZ_CREATED,
        {
            "quiz_id": quiz.pk,
            "course_id": course.pk,
            "course_title": course.title,
            "quiz_title": quiz.title,
            "max_score": float(quiz.max_score),
        },
    )
    return quiz


# ----- Lesson Activity -----


def track_lesson_watch(
    *, student: User, lesson_id: int, watch_duration_seconds: int = 0
) -> LessonActivity:
    """Track watch time for a lesson. Upserts LessonActivity, increments duration."""
    lesson = get_lesson_or_404(lesson_id)
    if not is_student_enrolled_in_course(student, lesson.course_id):
        raise PermissionDenied("You are not enrolled in this course.")

    activity, _ = LessonActivity.objects.get_or_create(
        student=student,
        lesson=lesson,
        defaults={"last_opened_at": timezone.now()},
    )
    if watch_duration_seconds > 0:
        activity.watch_duration_seconds += watch_duration_seconds
    activity.last_opened_at = timezone.now()
    activity.save()
    return activity


def complete_lesson(*, student: User, lesson_id: int) -> LessonActivity:
    """Mark a lesson as completed and trigger course progress update."""
    lesson = get_lesson_or_404(lesson_id)
    if not is_student_enrolled_in_course(student, lesson.course_id):
        raise PermissionDenied("You are not enrolled in this course.")

    activity, _ = LessonActivity.objects.get_or_create(
        student=student,
        lesson=lesson,
        defaults={"last_opened_at": timezone.now()},
    )
    if not activity.completed:
        activity.completed = True
        activity.last_opened_at = timezone.now()
        activity.save()

        EventBus.publish(
            Events.LESSON_COMPLETED,
            {
                "student_id": student.pk,
                "lesson_id": lesson_id,
                "course_id": lesson.course_id,
                "course_title": lesson.course.title,
                "lesson_title": lesson.title,
                "timestamp": timezone.now().isoformat(),
            },
        )

        update_progress(student=student, course=lesson.course)

    return activity


def get_lesson_attendance_summary(
    *, lesson_id: int, teacher: User
) -> LessonAttendanceSummary:
    """
    Teacher views attendance for all enrolled students in a lesson.

    Returns summary with all enrolled students and their attendance status.
    """
    lesson = get_lesson_or_404(lesson_id)

    if lesson.course.teacher_id != teacher.pk:
        from core.exceptions import PermissionDenied as PD

        raise PD("You do not have permission to view this attendance.")

    enrolled_student_ids = get_enrolled_student_ids(lesson.course_id)
    total_enrolled = len(enrolled_student_ids)

    from attendance.selectors import get_attendance_for_course

    attendance_records = get_attendance_for_course(
        lesson.course_id, date=lesson.start_time.date()
    )

    attendance_by_student = {
        record.student_id: record.status for record in attendance_records
    }

    attendance_list = []
    for student_id in enrolled_student_ids:
        from accounts.selectors import get_user_by_id

        user = get_user_by_id(student_id)
        attendance_list.append(
            {
                "student_id": student_id,
                "student_name": user.get_full_name() or user.username,
                "status": attendance_by_student.get(student_id),
            }
        )

    return LessonAttendanceSummary(
        lesson_id=lesson_id,
        lesson_title=lesson.title,
        total_enrolled=total_enrolled,
        attendance=attendance_list,
    )
