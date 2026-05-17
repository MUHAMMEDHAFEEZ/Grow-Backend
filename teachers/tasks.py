from __future__ import annotations

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_welcome_email(email: str, full_name: str):
    send_mail(
        subject="Welcome to Grow!",
        message=f"Hi {full_name},\n\nWelcome to Grow Educational Platform. Your teacher account is active.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=True,
    )


@shared_task
def send_otp_email(email: str, otp: str):
    send_mail(
        subject="Your OTP for Password Reset",
        message=f"Your OTP is: {otp}\n\nIt expires in 10 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=True,
    )


@shared_task
def notify_students_new_lecture(lesson_id: int):
    from courses.models import Lesson, StudentCourse
    try:
        lesson = Lesson.objects.select_related("course").get(pk=lesson_id)
    except Lesson.DoesNotExist:
        return
    enrolled = StudentCourse.objects.filter(
        course=lesson.course, is_active=True
    ).select_related("student")
    for enrollment in enrolled:
        student = enrollment.student
        from notifications.models import Notification
        Notification.objects.create(
            recipient=student,
            title=f"New Lesson: {lesson.title}",
            body=f"A new lesson '{lesson.title}' has been published in {lesson.course.title}.",
            event_type=Notification.EventType.LESSON_CREATED,
            related_course=lesson.course,
            related_content_id=lesson.id,
        )


@shared_task
def send_feedback_notification(submission_id: int):
    from submissions.models import Submission
    try:
        submission = Submission.objects.select_related("student", "assignment").get(pk=submission_id)
    except Submission.DoesNotExist:
        return
    from students.models import StudentNotification
    StudentNotification.objects.get_or_create(
        student=submission.student,
        type=StudentNotification.Type.FEEDBACK_RECEIVED,
        reference_id=submission.assignment.id,
        defaults={
            "reference_type": "assignment",
            "message": f"Your submission for '{submission.assignment.title}' has been graded.",
        },
    )


@shared_task
def schedule_assignment_reminder(assignment_id: int):
    pass  # placeholder — scheduled celery tasks to be implemented
