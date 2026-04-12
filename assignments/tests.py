"""
assignments/tests.py — Service-layer tests for assignment business logic.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.events import EventBus
from core.exceptions import NotFound, PermissionDenied
from courses import services as course_services
from assignments import services
from assignments.models import Assignment

User = get_user_model()


def _due():
    return timezone.make_aware(datetime.datetime(2027, 1, 1))


class AssignmentServiceTest(TestCase):
    def setUp(self):
        EventBus.clear()
        self.teacher = User.objects.create_user(
            username="teacher1", email="t1@grow.io", password="pass", role="teacher"
        )
        self.other_teacher = User.objects.create_user(
            username="teacher2", email="t2@grow.io", password="pass", role="teacher"
        )
        self.student = User.objects.create_user(
            username="student1", email="s1@grow.io", password="pass", role="student"
        )
        self.course = course_services.create_course(teacher=self.teacher, title="Math 101")

    def test_create_by_teacher(self):
        assignment = services.create_assignment(
            teacher=self.teacher, course_id=self.course.pk,
            title="Quiz 1", description="Chapter 1", due_date=_due(),
        )
        self.assertEqual(assignment.title, "Quiz 1")
        self.assertEqual(assignment.course, self.course)
        self.assertEqual(assignment.created_by, self.teacher)

    def test_create_by_non_teacher_raises(self):
        with self.assertRaises(PermissionDenied):
            services.create_assignment(
                teacher=self.student, course_id=self.course.pk,
                title="Bad", description="", due_date=_due(),
            )

    def test_create_for_unowned_course_raises(self):
        with self.assertRaises(NotFound):
            services.create_assignment(
                teacher=self.other_teacher, course_id=self.course.pk,
                title="Stolen", description="", due_date=_due(),
            )

    def test_update_assignment(self):
        assignment = services.create_assignment(
            teacher=self.teacher, course_id=self.course.pk,
            title="Original", description="", due_date=_due(),
        )
        updated = services.update_assignment(
            assignment_id=assignment.pk, teacher=self.teacher, title="Updated"
        )
        self.assertEqual(updated.title, "Updated")

    def test_delete_assignment(self):
        assignment = services.create_assignment(
            teacher=self.teacher, course_id=self.course.pk,
            title="To Delete", description="", due_date=_due(),
        )
        services.delete_assignment(assignment_id=assignment.pk, teacher=self.teacher)
        self.assertFalse(Assignment.objects.filter(pk=assignment.pk).exists())

    def test_delete_by_wrong_teacher_raises(self):
        assignment = services.create_assignment(
            teacher=self.teacher, course_id=self.course.pk,
            title="Protected", description="", due_date=_due(),
        )
        with self.assertRaises(PermissionDenied):
            services.delete_assignment(assignment_id=assignment.pk, teacher=self.other_teacher)

    def test_event_published_on_create(self):
        received = []
        EventBus.subscribe("assignment_created", lambda p: received.append(p))
        assignment = services.create_assignment(
            teacher=self.teacher, course_id=self.course.pk,
            title="Notified", description="", due_date=_due(),
        )
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["assignment_id"], assignment.pk)
        self.assertEqual(received[0]["course_id"], self.course.pk)
        self.assertEqual(received[0]["teacher_id"], self.teacher.pk)
