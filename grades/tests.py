"""
grades/tests.py — Tests for submission grading service + event emission.
"""
import datetime

from django.utils import timezone

from django.test import TestCase
from django.contrib.auth import get_user_model

from core.events import EventBus
from core.exceptions import Conflict, PermissionDenied
from courses import services as course_services
from assignments.services import create_assignment
from submissions.services import submit_assignment
from grades.services import grade_submission
from grades.models import Grade
from submissions.models import Submission

User = get_user_model()


class GradeServiceTest(TestCase):
    def setUp(self):
        EventBus.clear()
        self.teacher = User.objects.create_user(
            username="teacher", email="t@g.io", password="pass", role="teacher"
        )
        self.student = User.objects.create_user(
            username="student", email="s@g.io", password="pass", role="student"
        )
        self.course = course_services.create_course(teacher=self.teacher, title="Bio")
        course_services.enroll_student(course_id=self.course.pk, student=self.student)
        self.assignment = create_assignment(
            teacher=self.teacher,
            course_id=self.course.pk,
            title="Lab Report",
            description="Write up the lab",
            due_date=timezone.make_aware(datetime.datetime(2026, 12, 31)),
        )
        self.submission = submit_assignment(
            student=self.student,
            assignment_id=self.assignment.pk,
            content="My lab report content.",
        )

    def test_grade_submission_success(self):
        grade = grade_submission(teacher=self.teacher, submission_id=self.submission.pk, score=90)
        self.assertEqual(grade.score, 90)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.Status.GRADED)

    def test_grade_twice_raises(self):
        grade_submission(teacher=self.teacher, submission_id=self.submission.pk, score=80)
        with self.assertRaises(Conflict):
            grade_submission(teacher=self.teacher, submission_id=self.submission.pk, score=70)

    def test_grade_emits_event(self):
        received = []
        EventBus.subscribe("submission_graded", lambda p: received.append(p))
        grade_submission(teacher=self.teacher, submission_id=self.submission.pk, score=95)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["score"], 95.0)
        self.assertEqual(received[0]["student_id"], self.student.pk)

    def test_wrong_teacher_cannot_grade(self):
        other = User.objects.create_user(
            username="other", email="o@g.io", password="pass", role="teacher"
        )
        with self.assertRaises(PermissionDenied):
            grade_submission(teacher=other, submission_id=self.submission.pk, score=50)
