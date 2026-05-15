from unittest.mock import patch

from django.test import TestCase

from core.exceptions import NotFound


class CeleryFailureTests(TestCase):
    """All teacher service functions must succeed even when Celery .delay() raises."""

    def _assert_delay_wrapped(self, service_func, *args, **kwargs):
        """Helper: patch all known task delay methods and assert service succeeds."""
        patchers = [
            patch("teachers.tasks.send_welcome_email.delay"),
            patch("teachers.tasks.send_otp_email.delay"),
            patch("teachers.tasks.notify_students_new_lecture.delay"),
            patch("teachers.tasks.schedule_assignment_reminder.delay"),
            patch("teachers.tasks.send_feedback_notification.delay"),
        ]
        for p in patchers:
            p.start()
        try:
            return service_func(*args, **kwargs)
        finally:
            for p in patchers:
                p.stop()

    def _run_task_delay_raises(self, service_func, *args, **kwargs):
        """Mock all task .delay() to raise ConnectionError and call the service."""
        patchers = [
            patch("teachers.tasks.send_welcome_email.delay", side_effect=ConnectionError("Redis refused")),
            patch("teachers.tasks.send_otp_email.delay", side_effect=ConnectionError("Redis refused")),
            patch("teachers.tasks.notify_students_new_lecture.delay", side_effect=ConnectionError("Redis refused")),
            patch("teachers.tasks.schedule_assignment_reminder.delay", side_effect=ConnectionError("Redis refused")),
            patch("teachers.tasks.send_feedback_notification.delay", side_effect=ConnectionError("Redis refused")),
        ]
        for p in patchers:
            p.start()
        try:
            return service_func(*args, **kwargs)
        finally:
            for p in patchers:
                p.stop()

    def _get_school(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin = User.objects.create_user(
            username="schooladmin",
            email="admin@school.com",
            password="testpass123",
            role=User.Role.SCHOOL_ADMIN,
        )
        from accounts.models import School
        return School.objects.create(
            name="Test School",
            created_by=admin,
        )

    def _get_teacher(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.create_user(
            username="testteacher",
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )

    def _get_student(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.create_user(
            username="teststudent",
            email="student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )

    def _get_course(self, teacher):
        from courses.models import Course
        return Course.objects.create(
            teacher=teacher,
            title="Test Course",
            description="Test Description",
        )

    def _get_submission(self, student, assignment):
        from submissions.models import Submission
        return Submission.objects.create(
            student=student,
            assignment=assignment,
            content="test",
        )

    # ── T005 / T012: create_teacher_lesson succeeds when .delay() raises ──

    def test_create_teacher_lesson_succeeds_when_delay_raises(self):
        from teachers.services import create_teacher_lesson

        teacher = self._get_teacher()
        course = self._get_course(teacher)
        lesson = self._run_task_delay_raises(
            create_teacher_lesson,
            teacher=teacher,
            course_id=course.pk,
            title="Test Lesson",
            content="Content",
            order=1,
            status="published",
        )
        self.assertIsNotNone(lesson)
        self.assertEqual(lesson.title, "Test Lesson")

    def test_create_teacher_lesson_succeeds_when_delay_succeeds(self):
        from teachers.services import create_teacher_lesson

        teacher = self._get_teacher()
        course = self._get_course(teacher)
        lesson = self._assert_delay_wrapped(
            create_teacher_lesson,
            teacher=teacher,
            course_id=course.pk,
            title="Test Lesson",
            content="Content",
            order=1,
            status="published",
        )
        self.assertIsNotNone(lesson)
        self.assertEqual(lesson.title, "Test Lesson")

    # ── T006 / T013: update_teacher_lesson succeeds when .delay() raises ──

    def test_update_teacher_lesson_succeeds_when_delay_raises(self):
        from teachers.services import create_teacher_lesson, update_teacher_lesson

        teacher = self._get_teacher()
        course = self._get_course(teacher)
        lesson = self._assert_delay_wrapped(
            create_teacher_lesson,
            teacher=teacher,
            course_id=course.pk,
            title="Original",
            content="Content",
            order=1,
            status="draft",
        )
        updated = self._run_task_delay_raises(
            update_teacher_lesson,
            teacher=teacher,
            lesson_id=lesson.pk,
            title="Updated",
            status="published",
        )
        self.assertEqual(updated.title, "Updated")

    def test_update_teacher_lesson_succeeds_when_delay_succeeds(self):
        from teachers.services import create_teacher_lesson, update_teacher_lesson

        teacher = self._get_teacher()
        course = self._get_course(teacher)
        lesson = self._assert_delay_wrapped(
            create_teacher_lesson,
            teacher=teacher,
            course_id=course.pk,
            title="Original",
            content="Content",
            order=1,
            status="draft",
        )
        updated = self._assert_delay_wrapped(
            update_teacher_lesson,
            teacher=teacher,
            lesson_id=lesson.pk,
            title="Updated",
            status="published",
        )
        self.assertEqual(updated.title, "Updated")

    # ── T007 / T014: signup_teacher succeeds when .delay() raises ──

    def test_signup_teacher_succeeds_when_delay_raises(self):
        from teachers.services import signup_teacher

        from teachers.models import TeacherCode
        school = self._get_school()
        TeacherCode.objects.create(
            code="TESTCODE123",
            school=school,
        )
        result = self._run_task_delay_raises(
            signup_teacher,
            school_id=school.pk,
            full_name="Test Teacher",
            email="signuptest@test.com",
            password="testpass123",
            teacher_code="TESTCODE123",
        )
        user, access_token, refresh_token = result
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "signuptest@test.com")
        self.assertTrue(access_token)
        self.assertTrue(refresh_token)

    def test_signup_teacher_succeeds_when_delay_succeeds(self):
        from teachers.services import signup_teacher

        from teachers.models import TeacherCode
        school = self._get_school()
        TeacherCode.objects.create(
            code="TESTCODE456",
            school=school,
        )
        result = self._assert_delay_wrapped(
            signup_teacher,
            school_id=school.pk,
            full_name="Test Teacher",
            email="signuptest2@test.com",
            password="testpass123",
            teacher_code="TESTCODE456",
        )
        user, access_token, refresh_token = result
        self.assertIsNotNone(user)
        self.assertTrue(access_token)

    # ── T008 / T015: send_otp succeeds when .delay() raises ──

    def test_send_otp_succeeds_when_delay_raises(self):
        from teachers.services import send_otp

        teacher = self._get_teacher()
        msg = self._run_task_delay_raises(send_otp, email=teacher.email)
        self.assertEqual(msg, "OTP sent to your email.")

    def test_send_otp_succeeds_when_delay_succeeds(self):
        from teachers.services import send_otp

        teacher = self._get_teacher()
        msg = self._assert_delay_wrapped(send_otp, email=teacher.email)
        self.assertEqual(msg, "OTP sent to your email.")

    def test_send_otp_raises_not_found_for_nonexistent_email(self):
        from teachers.services import send_otp

        with self.assertRaises(NotFound):
            self._assert_delay_wrapped(send_otp, email="nonexistent@test.com")

    # ── T009 / T016: create_teacher_assignment succeeds when .delay() raises ──

    def test_create_teacher_assignment_succeeds_when_delay_raises(self):
        from teachers.services import create_teacher_assignment

        teacher = self._get_teacher()
        course = self._get_course(teacher)
        from django.utils import timezone
        from datetime import timedelta
        assignment = self._run_task_delay_raises(
            create_teacher_assignment,
            teacher=teacher,
            course_id=course.pk,
            title="Test Assignment",
            description="Desc",
            due_date=timezone.now() + timedelta(days=7),
        )
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.title, "Test Assignment")

    def test_create_teacher_assignment_succeeds_when_delay_succeeds(self):
        from teachers.services import create_teacher_assignment

        teacher = self._get_teacher()
        course = self._get_course(teacher)
        from django.utils import timezone
        from datetime import timedelta
        assignment = self._assert_delay_wrapped(
            create_teacher_assignment,
            teacher=teacher,
            course_id=course.pk,
            title="Test Assignment",
            description="Desc",
            due_date=timezone.now() + timedelta(days=7),
        )
        self.assertIsNotNone(assignment)

    # ── T010 / T017: grade_submission succeeds when .delay() raises ──

    def test_grade_submission_succeeds_when_delay_raises(self):
        from teachers.services import grade_submission

        teacher = self._get_teacher()
        student = self._get_student()
        course = self._get_course(teacher)
        from assignments.models import Assignment
        from django.utils import timezone
        from datetime import timedelta
        assignment = Assignment.objects.create(
            course=course,
            created_by=teacher,
            title="Test Assignment",
            description="Desc",
            due_date=timezone.now() + timedelta(days=7),
            max_score=100,
            xp_reward=50,
        )
        submission = self._get_submission(student, assignment)

        graded = self._run_task_delay_raises(
            grade_submission,
            teacher=teacher,
            submission_id=submission.pk,
            raw_score=85.0,
            feedback="Good job!",
        )
        self.assertIsNotNone(graded)
        self.assertTrue(graded.is_graded)

    def test_grade_submission_succeeds_when_delay_succeeds(self):
        from teachers.services import grade_submission

        teacher = self._get_teacher()
        student = self._get_student()
        course = self._get_course(teacher)
        from assignments.models import Assignment
        from django.utils import timezone
        from datetime import timedelta
        assignment = Assignment.objects.create(
            course=course,
            created_by=teacher,
            title="Test Assignment",
            description="Desc",
            due_date=timezone.now() + timedelta(days=7),
            max_score=100,
            xp_reward=50,
        )
        submission = self._get_submission(student, assignment)

        graded = self._assert_delay_wrapped(
            grade_submission,
            teacher=teacher,
            submission_id=submission.pk,
            raw_score=85.0,
            feedback="Good job!",
        )
        self.assertIsNotNone(graded)
        self.assertTrue(graded.is_graded)

    # ── T020: Lesson persists in DB when .delay() raises inside on_commit ──

    def test_lesson_persists_in_db_when_delay_raises(self):
        from teachers.services import create_teacher_lesson
        from courses.models import Lesson

        teacher = self._get_teacher()
        course = self._get_course(teacher)
        lesson = self._run_task_delay_raises(
            create_teacher_lesson,
            teacher=teacher,
            course_id=course.pk,
            title="Persist Test",
            content="Content",
            order=1,
            status="published",
        )
        # Verify lesson exists in database via a fresh query
        saved = Lesson.objects.filter(pk=lesson.pk).first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.title, "Persist Test")

    # ── T021: Lesson update persists in DB when .delay() raises inside on_commit ──

    def test_lesson_update_persists_when_delay_raises(self):
        from teachers.services import create_teacher_lesson, update_teacher_lesson
        from courses.models import Lesson

        teacher = self._get_teacher()
        course = self._get_course(teacher)
        lesson = self._assert_delay_wrapped(
            create_teacher_lesson,
            teacher=teacher,
            course_id=course.pk,
            title="Original",
            content="Content",
            order=1,
            status="draft",
        )
        updated = self._run_task_delay_raises(
            update_teacher_lesson,
            teacher=teacher,
            lesson_id=lesson.pk,
            title="Updated Persist",
            status="published",
        )
        saved = Lesson.objects.filter(pk=updated.pk).first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.title, "Updated Persist")

    # ── T022: Assignment persists in DB when .delay() raises inside on_commit ──

    def test_assignment_persists_in_db_when_delay_raises(self):
        from teachers.services import create_teacher_assignment
        from assignments.models import Assignment

        teacher = self._get_teacher()
        course = self._get_course(teacher)
        from django.utils import timezone
        from datetime import timedelta
        assignment = self._run_task_delay_raises(
            create_teacher_assignment,
            teacher=teacher,
            course_id=course.pk,
            title="Assignment Persist",
            description="Desc",
            due_date=timezone.now() + timedelta(days=7),
        )
        saved = Assignment.objects.filter(pk=assignment.pk).first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.title, "Assignment Persist")
