"""
notifications/tests.py — Tests for notification service functions and event handlers.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.events import EventBus
from core.exceptions import NotFound, PermissionDenied
from courses import services as course_services
from assignments.services import create_assignment
from submissions.services import submit_assignment
from grades.services import grade_submission
from attendance.services import mark_attendance
from notifications.services import create_notification, mark_read, mark_all_read
from notifications.models import Notification
from notifications.handlers import register_handlers

User = get_user_model()


def _due():
    return timezone.make_aware(datetime.datetime(2027, 1, 1))


class NotificationServiceTest(TestCase):
    def setUp(self):
        EventBus.clear()
        self.user = User.objects.create_user(
            username="recipient", email="r@grow.io", password="pass", role="student"
        )
        self.other_user = User.objects.create_user(
            username="other", email="o@grow.io", password="pass", role="student"
        )

    def test_create_notification(self):
        notif = create_notification(
            recipient_id=self.user.pk,
            title="Test",
            body="Test body",
            event_type="assignment_created",
        )
        self.assertEqual(notif.recipient, self.user)
        self.assertFalse(notif.is_read)

    def test_mark_read(self):
        notif = create_notification(
            recipient_id=self.user.pk, title="T", body="B", event_type="enrollment_created"
        )
        result = mark_read(notification_id=notif.pk, user=self.user)
        self.assertTrue(result.is_read)

    def test_mark_read_wrong_user_raises(self):
        notif = create_notification(
            recipient_id=self.user.pk, title="T", body="B", event_type="enrollment_created"
        )
        with self.assertRaises(PermissionDenied):
            mark_read(notification_id=notif.pk, user=self.other_user)

    def test_mark_all_read(self):
        create_notification(recipient_id=self.user.pk, title="A", body="", event_type="enrollment_created")
        create_notification(recipient_id=self.user.pk, title="B", body="", event_type="enrollment_created")
        count = mark_all_read(user=self.user)
        self.assertEqual(count, 2)
        self.assertEqual(Notification.objects.filter(recipient=self.user, is_read=False).count(), 0)


class NotificationHandlerTest(TestCase):
    """Integration tests: event published → handler creates correct notifications."""

    def setUp(self):
        EventBus.clear()
        register_handlers()
        self.teacher = User.objects.create_user(
            username="teacher", email="t@grow.io", password="pass", role="teacher"
        )
        self.student = User.objects.create_user(
            username="student", email="s@grow.io", password="pass", role="student"
        )
        self.parent = User.objects.create_user(
            username="parent", email="p@grow.io", password="pass", role="parent"
        )
        self.course = course_services.create_course(teacher=self.teacher, title="Science")
        course_services.enroll_student(course_id=self.course.pk, student=self.student)
        self.assignment = create_assignment(
            teacher=self.teacher, course_id=self.course.pk,
            title="Lab", description="", due_date=_due(),
        )

    def test_on_assignment_created(self):
        # Enrollment happens in setUp, reset notifications created by enrollment event
        Notification.objects.all().delete()
        EventBus.clear()
        register_handlers()
        create_assignment(
            teacher=self.teacher, course_id=self.course.pk,
            title="New Assignment", description="", due_date=_due(),
        )
        notif = Notification.objects.filter(recipient=self.student, event_type="assignment_created").first()
        self.assertIsNotNone(notif)
        self.assertIn("New Assignment", notif.title)

    def test_on_submission_created(self):
        Notification.objects.all().delete()
        submission = submit_assignment(
            student=self.student, assignment_id=self.assignment.pk, content="My work"
        )
        notif = Notification.objects.filter(recipient=self.teacher, event_type="submission_created").first()
        self.assertIsNotNone(notif)

    def test_on_submission_graded(self):
        submission = submit_assignment(
            student=self.student, assignment_id=self.assignment.pk, content="My work"
        )
        Notification.objects.all().delete()
        grade_submission(teacher=self.teacher, submission_id=submission.pk, score=88)
        notif = Notification.objects.filter(recipient=self.student, event_type="submission_graded").first()
        self.assertIsNotNone(notif)
        self.assertIn("88", notif.body)

    def test_on_attendance_marked_absent(self):
        from accounts.models import ParentProfile
        ParentProfile.objects.create(parent=self.parent, child=self.student)
        Notification.objects.all().delete()
        mark_attendance(
            teacher=self.teacher, course_id=self.course.pk,
            date=datetime.date(2026, 4, 10),
            records=[{"student_id": self.student.pk, "status": "absent"}],
        )
        notif = Notification.objects.filter(recipient=self.parent, event_type="attendance_marked").first()
        self.assertIsNotNone(notif)
        self.assertIn("absent", notif.body.lower())

    def test_on_attendance_marked_present(self):
        Notification.objects.all().delete()
        mark_attendance(
            teacher=self.teacher, course_id=self.course.pk,
            date=datetime.date(2026, 4, 11),
            records=[{"student_id": self.student.pk, "status": "present"}],
        )
        self.assertEqual(
            Notification.objects.filter(event_type="attendance_marked").count(), 0
        )

    def test_on_enrollment_created(self):
        new_student = User.objects.create_user(
            username="new_s", email="ns@grow.io", password="pass", role="student"
        )
        Notification.objects.all().delete()
        course_services.enroll_student(course_id=self.course.pk, student=new_student)
        notif = Notification.objects.filter(recipient=new_student, event_type="enrollment_created").first()
        self.assertIsNotNone(notif)
        self.assertIn(self.course.title, notif.body)
