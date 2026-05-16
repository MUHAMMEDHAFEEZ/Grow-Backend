from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from core.exceptions import Conflict, NotFound, PermissionDenied, ValidationError
from courses.models import (
    AnswerOption,
    Course,
    Lesson,
    Question,
    Quiz,
)
from schools.models import Grade
from submissions.models import Submission
from xp.models import XPTransaction

from schools.services.registration_code_service import validate_and_consume_code

from .models import (
    AuditLog,
    DeviceSession,
    OTPRecord,
    RefreshToken,
    TeacherCode,
    TeacherNotification,
    TeacherNotificationPreference,
    TeacherProfile,
)

User = get_user_model()
logger = logging.getLogger(__name__)


def _safe_delay_welcome_email(email: str, full_name: str) -> None:
    from teachers.tasks import send_welcome_email
    try:
        send_welcome_email.delay(email, full_name)
    except Exception as e:
        logger.warning(
            "Failed to send welcome email to %s: %s", email, e, exc_info=True
        )


def _safe_delay_otp_email(email: str, otp: str) -> None:
    from teachers.tasks import send_otp_email
    try:
        send_otp_email.delay(email, otp)
    except Exception as e:
        logger.warning(
            "Failed to send OTP email to %s: %s", email, e, exc_info=True
        )


def _safe_delay_notify_students(lesson_id: int) -> None:
    from teachers.tasks import notify_students_new_lecture
    try:
        notify_students_new_lecture.delay(lesson_id)
    except Exception as e:
        logger.warning(
            "Failed to notify students for lesson %s: %s", lesson_id, e, exc_info=True
        )


def _safe_delay_schedule_reminder(assignment_id: int) -> None:
    from teachers.tasks import schedule_assignment_reminder
    try:
        schedule_assignment_reminder.delay(assignment_id)
    except Exception as e:
        logger.warning(
            "Failed to schedule reminder for assignment %s: %s", assignment_id, e, exc_info=True
        )


def _safe_delay_feedback_notification(submission_id: int) -> None:
    from teachers.tasks import send_feedback_notification
    try:
        send_feedback_notification.delay(submission_id)
    except Exception as e:
        logger.warning(
            "Failed to send feedback notification for submission %s: %s", submission_id, e, exc_info=True
        )


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _generate_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def _log_audit(actor_type: str, actor_id: int, action: str, resource_type: str, resource_id: int | None = None, metadata: dict | None = None, ip_address: str | None = None):
    AuditLog.objects.create(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata or {},
        ip_address=ip_address,
    )


# ── Auth ──


@transaction.atomic
def signup_teacher(*, school_id: int, full_name: str, email: str, password: str, teacher_code: str, ip_address: str | None = None) -> tuple[User, str, str]:
    if User.objects.filter(email=email).exists():
        raise Conflict("A user with this email already exists.")

    code_obj = validate_and_consume_code(
        code=teacher_code,
        school_id=school_id,
        code_type="teacher",
        user=None,
    )

    user = User.objects.create_user(
        username=email.split("@")[0],
        email=email,
        password=password,
        role=User.Role.TEACHER,
    )
    user.first_name = full_name.split()[0] if full_name.split() else ""
    user.last_name = " ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else ""
    user.save(update_fields=["first_name", "last_name"])

    code_obj.used_by = user
    code_obj.save(update_fields=["used_by"])

    TeacherProfile.objects.create(
        user=user,
        school_id=school_id,
    )
    TeacherNotificationPreference.objects.create(teacher=user)

    access_token = _create_access_token(user)
    refresh_token_str = _create_refresh_token(user, ip_address=ip_address)

    _log_audit("teacher", user.id, "signup", "User", user.id, ip_address=ip_address)

    transaction.on_commit(lambda: _safe_delay_welcome_email(email, full_name))

    return user, access_token, refresh_token_str


def _create_access_token(user: User) -> str:
    from rest_framework_simplejwt.tokens import AccessToken
    token = AccessToken.for_user(user)
    token.set_exp(lifetime=settings.TEACHER_ACCESS_TOKEN_LIFETIME)
    return str(token)


def _create_refresh_token(user: User, ip_address: str | None = None, device_info: str = "") -> str:
    raw_token = secrets.token_urlsafe(64)
    token_hash = _hash_token(raw_token)
    RefreshToken.objects.create(
        teacher=user,
        token_hash=token_hash,
        expires_at=timezone.now() + settings.TEACHER_REFRESH_TOKEN_LIFETIME,
        ip_address=ip_address,
        device_info=device_info,
    )
    return raw_token


def login_teacher(*, school_id: int, email: str, password: str, ip_address: str | None = None, device_info: str = "") -> tuple[User, str, str]:
    from django.contrib.auth import authenticate

    user = authenticate(username=email, password=password)
    if not user or user.role != User.Role.TEACHER:
        raise ValidationError("Invalid email or password.")

    profile = getattr(user, "teacher_profile", None)
    if profile is None or profile.school_id != school_id:
        raise ValidationError("Invalid email or password.")

    if profile.status != TeacherProfile.Status.ACTIVE:
        raise PermissionDenied("Your account is not active.")

    DeviceSession.objects.create(
        teacher=user,
        refresh_token_hash="",  # will be updated on refresh
        ip_address=ip_address,
        device_info=device_info,
    )

    access_token = _create_access_token(user)
    refresh_token_str = _create_refresh_token(user, ip_address=ip_address, device_info=device_info)

    _log_audit("teacher", user.id, "login", "User", user.id, ip_address=ip_address)
    return user, access_token, refresh_token_str


def refresh_teacher_token(*, refresh_token: str) -> tuple[str, str]:
    token_hash = _hash_token(refresh_token)
    try:
        stored = RefreshToken.objects.get(token_hash=token_hash, is_revoked=False)
    except RefreshToken.DoesNotExist:
        raise ValidationError("Invalid or revoked refresh token.")

    if stored.expires_at < timezone.now():
        stored.is_revoked = True
        stored.save(update_fields=["is_revoked"])
        raise ValidationError("Refresh token has expired.")

    user = stored.teacher
    stored.is_revoked = True
    stored.save(update_fields=["is_revoked"])

    new_access_token = _create_access_token(user)
    new_refresh_token = _create_refresh_token(
        user, ip_address=stored.ip_address, device_info=stored.device_info
    )

    return new_access_token, new_refresh_token


def logout_teacher(*, refresh_token: str):
    token_hash = _hash_token(refresh_token)
    RefreshToken.objects.filter(token_hash=token_hash).update(is_revoked=True)


# ── OTP / Password Reset ──


def send_otp(*, email: str) -> str:
    if not User.objects.filter(email=email, role=User.Role.TEACHER).exists():
        raise NotFound("No teacher found with this email.")

    with transaction.atomic():
        OTPRecord.objects.filter(email=email, is_used=False).update(is_used=True)

        otp = _generate_otp()
        otp_hash = _hash_token(otp)
        OTPRecord.objects.create(
            email=email,
            otp_hash=otp_hash,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        transaction.on_commit(lambda: _safe_delay_otp_email(email, otp))

    return "OTP sent to your email."


def verify_otp(*, email: str, otp: str) -> str:
    otp_hash = _hash_token(otp)
    try:
        record = OTPRecord.objects.filter(
            email=email, otp_hash=otp_hash, is_used=False, expires_at__gte=timezone.now()
        ).latest("created_at")
    except OTPRecord.DoesNotExist:
        raise ValidationError("Invalid or expired OTP.")

    record.is_used = True
    record.save(update_fields=["is_used"])

    reset_token = secrets.token_urlsafe(32)
    return reset_token


def reset_password(*, reset_token: str, new_password: str):
    pass


def change_password(*, user: User, new_password: str):
    user.set_password(new_password)
    user.save(update_fields=["password"])
    RefreshToken.objects.filter(teacher=user, is_revoked=False).update(is_revoked=True)
    _log_audit("teacher", user.id, "password_reset", "User", user.id)


# ── Course ──


def create_teacher_course(*, teacher: User, title: str, description: str = "", grade_id: int | None = None, is_published: bool = False, grade=None) -> Course:
    resolved_grade_id = getattr(grade, "pk", grade) or grade_id
    grade_obj = grade if isinstance(grade, Grade) else Grade.objects.filter(pk=resolved_grade_id).first()
    school_id = grade_obj.school_id if grade_obj else None
    course = Course.objects.create(
        teacher=teacher,
        title=title,
        description=description,
        grade_id=resolved_grade_id,
        is_published=is_published,
        school_id=school_id,
    )
    _log_audit("teacher", teacher.id, "create", "Course", course.id)
    return course


def update_teacher_course(*, teacher: User, course_id: int, **fields) -> Course:
    try:
        course = Course.objects.get(pk=course_id, teacher=teacher)
    except Course.DoesNotExist:
        raise NotFound("Course not found or you do not own it.")
    for key, value in fields.items():
        setattr(course, key, value)
    course.save()
    _log_audit("teacher", teacher.id, "update", "Course", course.id)
    return course


def delete_teacher_course(*, teacher: User, course_id: int):
    try:
        course = Course.objects.get(pk=course_id, teacher=teacher)
    except Course.DoesNotExist:
        raise NotFound("Course not found or you do not own it.")
    course.delete()
    _log_audit("teacher", teacher.id, "delete", "Course", course_id)


def create_teacher_lesson(*, teacher: User, course_id: int, **fields) -> Lesson:
    with transaction.atomic():
        try:
            course = Course.objects.get(pk=course_id, teacher=teacher)
        except Course.DoesNotExist:
            raise NotFound("Course not found or you do not own it.")
        lesson = Lesson.objects.create(course=course, **fields)
        _log_audit("teacher", teacher.id, "create", "Lesson", lesson.id)

        if lesson.status == Lesson.Status.PUBLISHED:
            transaction.on_commit(lambda: _safe_delay_notify_students(lesson.id))

        return lesson


def update_teacher_lesson(*, teacher: User, lesson_id: int, **fields) -> Lesson:
    with transaction.atomic():
        try:
            lesson = Lesson.objects.select_related("course").get(pk=lesson_id, course__teacher=teacher)
        except Lesson.DoesNotExist:
            raise NotFound("Lesson not found or you do not own it.")
        for key, value in fields.items():
            setattr(lesson, key, value)
        lesson.save()
        _log_audit("teacher", teacher.id, "update", "Lesson", lesson.id)

        if lesson.status == Lesson.Status.PUBLISHED:
            transaction.on_commit(lambda: _safe_delay_notify_students(lesson.id))

        return lesson


@transaction.atomic
def reorder_lessons(*, teacher: User, course_id: int, ordered_ids: list[int]) -> list[Lesson]:
    try:
        course = Course.objects.get(pk=course_id, teacher=teacher)
    except Course.DoesNotExist:
        raise NotFound("Course not found or you do not own it.")

    existing = set(
        Lesson.objects.filter(course=course).values_list("pk", flat=True)
    )
    provided = set(ordered_ids)
    if not provided.issubset(existing):
        missing = provided - existing
        raise ValidationError(
            f"Lesson IDs {sorted(missing)} do not belong to this course."
        )
    if provided != existing:
        raise ValidationError(
            "ordered_ids must include all lessons in the course."
        )

    from django.db.models import Case, Value, When, IntegerField

    cases = [
        When(pk=pk, then=Value(index))
        for index, pk in enumerate(ordered_ids)
    ]
    Lesson.objects.filter(course=course).update(
        order=Case(*cases, output_field=IntegerField())
    )

    _log_audit("teacher", teacher.id, "reorder", "Lesson", course_id)

    return list(Lesson.objects.filter(pk__in=ordered_ids).order_by("order"))


def delete_teacher_lesson(*, teacher: User, lesson_id: int):
    try:
        lesson = Lesson.objects.select_related("course").get(pk=lesson_id, course__teacher=teacher)
    except Lesson.DoesNotExist:
        raise NotFound("Lesson not found or you do not own it.")
    lesson.delete()
    _log_audit("teacher", teacher.id, "delete", "Lesson", lesson_id)


# ── Assignment ──


def create_teacher_assignment(*, teacher: User, course_id: int, **fields) -> Assignment:
    from assignments.models import Assignment
    with transaction.atomic():
        try:
            course = Course.objects.get(pk=course_id, teacher=teacher)
        except Course.DoesNotExist:
            raise NotFound("Course not found or you do not own it.")
        if fields.get("due_date", timezone.now()) < timezone.now():
            raise ValidationError("Due date must be in the future.")
        assignment = Assignment.objects.create(
            course=course,
            created_by=teacher,
            **fields,
        )
        _log_audit("teacher", teacher.id, "create", "Assignment", assignment.id)

        transaction.on_commit(lambda: _safe_delay_schedule_reminder(assignment.id))

    return assignment


def update_teacher_assignment(*, teacher: User, assignment_id: int, **fields) -> Assignment:
    from assignments.models import Assignment
    try:
        assignment = Assignment.objects.select_related("course").get(
            pk=assignment_id, course__teacher=teacher
        )
    except Assignment.DoesNotExist:
        raise NotFound("Assignment not found or you do not own it.")
    for key, value in fields.items():
        setattr(assignment, key, value)
    assignment.save()
    _log_audit("teacher", teacher.id, "update", "Assignment", assignment.id)
    return assignment


def delete_teacher_assignment(*, teacher: User, assignment_id: int):
    from assignments.models import Assignment
    try:
        assignment = Assignment.objects.select_related("course").get(
            pk=assignment_id, course__teacher=teacher
        )
    except Assignment.DoesNotExist:
        raise NotFound("Assignment not found or you do not own it.")
    assignment.delete()
    _log_audit("teacher", teacher.id, "delete", "Assignment", assignment_id)


# ── Grade Submission ──


@transaction.atomic
def grade_submission(*, teacher: User, submission_id: int, raw_score: float, feedback: str = "", ip_address: str | None = None) -> Submission:
    submission = get_submission_or_404(submission_id)

    if submission.assignment.course.teacher_id != teacher.id:
        raise PermissionDenied("You can only grade submissions for your own assignments.")

    assignment = submission.assignment
    max_score = float(assignment.max_score)
    normalized_score = (raw_score / max_score) * 100 if max_score > 0 else 0

    is_late = submission.submitted_at > assignment.due_date
    xp_awarded = assignment.xp_reward
    if is_late:
        xp_awarded = max(0, xp_awarded - assignment.late_penalty_xp)

    submission.raw_score = raw_score
    submission.normalized_score = normalized_score
    submission.xp_awarded = xp_awarded
    submission.feedback = feedback
    submission.is_graded = True
    submission.status = Submission.Status.GRADED
    submission.save()

    XPTransaction.objects.get_or_create(
        student=submission.student,
        source_type=XPTransaction.SourceType.ASSIGNMENT.value,
        source_id=assignment.id,
        defaults={
            "xp_amount": xp_awarded,
            "source": XPTransaction.Source.ASSIGNMENT.value,
        },
    )

    _log_audit(
        "teacher", teacher.id, "grade", "Submission", submission.id,
        metadata={"assignment_id": assignment.id, "score": raw_score, "xp_awarded": xp_awarded},
        ip_address=ip_address,
    )

    transaction.on_commit(lambda: _safe_delay_feedback_notification(submission.id))

    return submission


def get_submission_or_404(submission_id: int) -> Submission:
    try:
        return Submission.objects.select_related("student", "assignment__course").get(pk=submission_id)
    except Submission.DoesNotExist:
        raise NotFound("Submission not found.")


# ── Quiz ──


@transaction.atomic
def create_teacher_quiz(*, teacher: User, **data) -> Quiz:
    course_id = data.pop("course_id")
    try:
        course = Course.objects.get(pk=course_id, teacher=teacher)
    except Course.DoesNotExist:
        raise NotFound("Course not found or you do not own it.")

    lesson_id = data.pop("lesson_id", None)
    questions_data = data.pop("questions", [])

    if data.get("end_time") <= data.get("start_time"):
        raise ValidationError("end_time must be after start_time.")
    if data.get("start_time") <= timezone.now():
        raise ValidationError("start_time must be in the future.")

    quiz = Quiz.objects.create(
        course=course,
        teacher=teacher,
        lesson_id=lesson_id,
        **data,
    )

    for q_data in questions_data:
        options_data = q_data.pop("options", [])
        question = Question.objects.create(quiz=quiz, **q_data)
        for opt_data in options_data:
            AnswerOption.objects.create(question=question, **opt_data)

        correct_count = sum(1 for o in options_data if o.get("is_correct"))
        if correct_count != 1:
            raise ValidationError(f"Question '{q_data['text'][:50]}...' must have exactly one correct answer.")

    _log_audit("teacher", teacher.id, "create", "Quiz", quiz.id)
    return quiz


def update_teacher_quiz(*, teacher: User, quiz_id: int, **data) -> Quiz:
    try:
        quiz = Quiz.objects.get(pk=quiz_id, teacher=teacher)
    except Quiz.DoesNotExist:
        raise NotFound("Quiz not found or you do not own it.")

    if quiz.is_locked:
        from rest_framework.exceptions import APIException
        raise APIException("Quiz is locked. Cannot edit after first submission.", code=423)

    questions_data = data.pop("questions", None)
    for key, value in data.items():
        setattr(quiz, key, value)
    quiz.save()

    if questions_data is not None:
        quiz.questions.all().delete()
        for q_data in questions_data:
            options_data = q_data.pop("options", [])
            question = Question.objects.create(quiz=quiz, **q_data)
            for opt_data in options_data:
                AnswerOption.objects.create(question=question, **opt_data)

    _log_audit("teacher", teacher.id, "update", "Quiz", quiz.id)
    return quiz


def send_quiz_feedback(*, teacher: User, quiz_id: int, student_id: int, message: str):
    if not Quiz.objects.filter(pk=quiz_id, teacher=teacher).exists():
        raise NotFound("Quiz not found or you do not own it.")

    try:
        student = User.objects.get(pk=student_id, role=User.Role.STUDENT)
    except User.DoesNotExist:
        raise NotFound("Student not found.")

    TeacherNotification.objects.create(
        teacher=teacher,
        event_type=TeacherNotification.EventType.GRADE_UPDATE,
        reference_type="Quiz",
        reference_id=quiz_id,
        message=f"Feedback for {student.username}: {message}",
    )


# ── Teacher Profile Settings ──


def update_teacher_profile(*, user: User, **data) -> TeacherProfile:
    profile, _ = TeacherProfile.objects.get_or_create(
        user=user,
        defaults={"school_id": user.school_id or 1},
    )
    full_name = data.pop("full_name", None)
    if full_name:
        parts = full_name.split()
        if parts:
            user.first_name = parts[0]
            user.last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
            user.save(update_fields=["first_name", "last_name"])

    for key, value in data.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    profile.save()
    _log_audit("teacher", user.id, "update", "TeacherProfile", profile.id)
    return profile


def update_notification_preferences(*, user: User, **data) -> TeacherNotificationPreference:
    prefs, _ = TeacherNotificationPreference.objects.get_or_create(teacher=user)
    for key, value in data.items():
        if hasattr(prefs, key):
            setattr(prefs, key, value)
    prefs.save()
    return prefs
