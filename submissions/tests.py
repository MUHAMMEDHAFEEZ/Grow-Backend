"""
submissions/tests.py — Service-layer tests for assignment submission logic.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.events import EventBus
from core.exceptions import Conflict, NotFound, PermissionDenied
from courses import services as course_services
from assignments.services import create_assignment
from submissions import services
from submissions.models import Submission

User = get_user_model()


def _due():
    return timezone.make_aware(datetime.datetime(2027, 1, 1))


class SubmissionServiceTest(TestCase):
    def setUp(self):
        EventBus.clear()
        self.teacher = User.objects.create_user(
            username="teacher1", email="t1@grow.io", password="pass", role="teacher"
        )
        self.student = User.objects.create_user(
            username="student1", email="s1@grow.io", password="pass", role="student"
        )
        self.other_student = User.objects.create_user(
            username="student2", email="s2@grow.io", password="pass", role="student"
        )
        self.course = course_services.create_course(teacher=self.teacher, title="Bio")
        course_services.enroll_student(course_id=self.course.pk, student=self.student)
        self.assignment = create_assignment(
            teacher=self.teacher, course_id=self.course.pk,
            title="Lab Report", description="Write it up", due_date=_due(),
        )

    def test_submit_while_enrolled(self):
        sub = services.submit_assignment(
            student=self.student, assignment_id=self.assignment.pk, content="My answer"
        )
        self.assertEqual(sub.student, self.student)
        self.assertEqual(sub.status, Submission.Status.PENDING)

    def test_submit_without_enrollment_raises(self):
        with self.assertRaises(PermissionDenied):
            services.submit_assignment(
                student=self.other_student, assignment_id=self.assignment.pk, content="..."
            )

    def test_submit_as_non_student_raises(self):
        with self.assertRaises(PermissionDenied):
            services.submit_assignment(
                student=self.teacher, assignment_id=self.assignment.pk, content="..."
            )

    def test_duplicate_submit_raises(self):
        services.submit_assignment(
            student=self.student, assignment_id=self.assignment.pk, content="First"
        )
        with self.assertRaises(Conflict):
            services.submit_assignment(
                student=self.student, assignment_id=self.assignment.pk, content="Second"
            )

    def test_event_published_on_submit(self):
        received = []
        EventBus.subscribe("submission_created", lambda p: received.append(p))
        services.submit_assignment(
            student=self.student, assignment_id=self.assignment.pk, content="Event test"
        )
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["student_id"], self.student.pk)
        self.assertEqual(received[0]["teacher_id"], self.teacher.pk)
        self.assertEqual(received[0]["assignment_id"], self.assignment.pk)
