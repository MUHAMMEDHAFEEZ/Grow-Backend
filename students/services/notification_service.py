from django.utils import timezone

from courses.models import Course
from students.models import StudentNotification, Student


def notify_new_lecture(lecture):
    course = lecture.course
    students = Student.objects.filter(grade=course.grade)

    for student in students:
        StudentNotification.objects.get_or_create(
            student=student.user,
            type="new_lesson",
            reference_id=lecture.id,
            defaults={
                "reference_type": "lesson",
                "message": f"New lecture: {lecture.title}",
            },
        )


def notify_assignment_reminder(assignment):
    students = Student.objects.filter(grade=assignment.course.grade)

    for student in students:
        StudentNotification.objects.get_or_create(
            student=student.user,
            type="deadline_reminder",
            reference_id=assignment.id,
            defaults={
                "reference_type": "assignment",
                "message": f"Reminder: '{assignment.title}' is due soon",
            },
        )


def notify_feedback_received(submission):
    StudentNotification.objects.get_or_create(
        student=submission.student,
        type="feedback_received",
        reference_id=submission.id,
        defaults={
            "reference_type": "submission",
            "message": f"Feedback received for '{submission.assignment.title}'",
        },
    )
