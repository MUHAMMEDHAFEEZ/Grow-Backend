"""
courses/tests.py — Unit tests for course services.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model

from core.events import EventBus
from core.exceptions import Conflict, PermissionDenied, NotFound, RateLimitExceeded
from courses.models import Course, Lesson, LessonActivity, Quiz, QuizAttempt, StudentCourse
from courses import services

User = get_user_model()


class CourseServiceTest(TestCase):
    def setUp(self):
        EventBus.clear()
        self.teacher = User.objects.create_user(
            username="teacher1", email="t@grow.io", password="pass", role="teacher"
        )
        self.student = User.objects.create_user(
            username="student1", email="s@grow.io", password="pass", role="student"
        )

    def test_create_course_by_teacher(self):
        course = services.create_course(teacher=self.teacher, title="Math 101")
        self.assertEqual(course.title, "Math 101")
        self.assertEqual(course.teacher, self.teacher)

    def test_create_course_by_student_raises(self):
        with self.assertRaises(PermissionDenied):
            services.create_course(teacher=self.student, title="Fail")

    def test_enroll_student(self):
        course = services.create_course(teacher=self.teacher, title="Science")
        sc = services.enroll_student(course_id=course.pk, student=self.student)
        self.assertEqual(sc.student, self.student)
        self.assertTrue(sc.is_active)

    def test_enroll_duplicate_returns_existing(self):
        course = services.create_course(teacher=self.teacher, title="History")
        sc1 = services.enroll_student(course_id=course.pk, student=self.student)
        sc2 = services.enroll_student(course_id=course.pk, student=self.student)
        self.assertEqual(sc1.pk, sc2.pk)
        self.assertEqual(sc1.student, sc2.student)

    def test_enroll_teacher_raises(self):
        course = services.create_course(teacher=self.teacher, title="Art")
        with self.assertRaises(PermissionDenied):
            services.enroll_student(course_id=course.pk, student=self.teacher)

    def test_delete_course_wrong_teacher_raises(self):
        other_teacher = User.objects.create_user(
            username="t2", email="t2@grow.io", password="pass", role="teacher"
        )
        course = services.create_course(teacher=self.teacher, title="Physics")
        with self.assertRaises(PermissionDenied):
            services.delete_course(course_id=course.pk, teacher=other_teacher)


class LessonActivityServiceTest(TestCase):
    def setUp(self):
        EventBus.clear()
        self.teacher = User.objects.create_user(
            username="t_act", email="tact@grow.io", password="pass", role="teacher"
        )
        self.student = User.objects.create_user(
            username="s_act", email="sact@grow.io", password="pass", role="student"
        )
        self.course = services.create_course(
            teacher=self.teacher, title="Lesson Test Course"
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Chapter 1",
            content="Lesson content",
            order=1,
        )
        # Enroll student
        services.enroll_student(course_id=self.course.pk, student=self.student)

    def test_track_watch_accumulates_duration(self):
        """Watch duration should accumulate across multiple track calls."""
        a1 = services.track_lesson_watch(
            student=self.student, lesson_id=self.lesson.pk, watch_duration_seconds=120
        )
        self.assertEqual(a1.watch_duration_seconds, 120)

        a2 = services.track_lesson_watch(
            student=self.student, lesson_id=self.lesson.pk, watch_duration_seconds=60
        )
        self.assertEqual(a2.watch_duration_seconds, 180)

    def test_track_watch_zero_default(self):
        """Calling track with no increment should still upsert and update last_opened_at."""
        a = services.track_lesson_watch(
            student=self.student, lesson_id=self.lesson.pk
        )
        self.assertEqual(a.watch_duration_seconds, 0)
        self.assertIsNotNone(a.last_opened_at)

    def test_complete_lesson_marks_completed(self):
        """Completing a lesson should set completed=True."""
        a = services.complete_lesson(
            student=self.student, lesson_id=self.lesson.pk
        )
        self.assertTrue(a.completed)

    def test_complete_lesson_idempotent(self):
        """Completing an already completed lesson should not raise."""
        a1 = services.complete_lesson(
            student=self.student, lesson_id=self.lesson.pk
        )
        a2 = services.complete_lesson(
            student=self.student, lesson_id=self.lesson.pk
        )
        self.assertTrue(a2.completed)
        self.assertEqual(a1.pk, a2.pk)

    def test_lesson_completion_triggers_course_progress(self):
        """Completing a lesson should create/update CourseProgress for the parent course."""
        services.complete_lesson(
            student=self.student, lesson_id=self.lesson.pk
        )
        from courses.models import CourseProgress
        cp = CourseProgress.objects.filter(
            student=self.student, course=self.course
        ).first()
        self.assertIsNotNone(cp)
        self.assertEqual(cp.completion_status, CourseProgress.CompletionStatus.IN_PROGRESS)

    def test_unique_constraint_prevents_duplicate(self):
        """Creating two LessonActivity records for same (student, lesson) should reuse one."""
        a1, _ = LessonActivity.objects.get_or_create(
            student=self.student, lesson=self.lesson
        )
        a2, _ = LessonActivity.objects.get_or_create(
            student=self.student, lesson=self.lesson
        )
        self.assertEqual(a1.pk, a2.pk)

    def test_track_unenrolled_student_raises(self):
        """A student not enrolled in the course cannot track lesson activity."""
        other = User.objects.create_user(
            username="other_s", email="os@grow.io", password="pass", role="student"
        )
        with self.assertRaises(PermissionDenied):
            services.track_lesson_watch(
                student=other, lesson_id=self.lesson.pk, watch_duration_seconds=10
            )

    def test_complete_unenrolled_student_raises(self):
        """A student not enrolled in the course cannot complete a lesson."""
        other = User.objects.create_user(
            username="other_s2", email="os2@grow.io", password="pass", role="student"
        )
        with self.assertRaises(PermissionDenied):
            services.complete_lesson(
                student=other, lesson_id=self.lesson.pk
            )


class QuizAttemptServiceTest(TestCase):
    def setUp(self):
        EventBus.clear()
        self.teacher = User.objects.create_user(
            username="t_quiz", email="tquiz@grow.io", password="pass", role="teacher"
        )
        self.student = User.objects.create_user(
            username="s_quiz", email="squiz@grow.io", password="pass", role="student"
        )
        self.course = services.create_course(
            teacher=self.teacher, title="Quiz Test Course"
        )
        self.quiz = Quiz.objects.create(
            course=self.course,
            title="Chapter 1 Quiz",
            max_score=100,
        )
        services.enroll_student(course_id=self.course.pk, student=self.student)

    def test_submit_attempt_auto_increments_number(self):
        """Attempt number should auto-increment from 1."""
        a1 = services.submit_quiz_attempt(
            student=self.student, quiz_id=self.quiz.pk, score=70.0
        )
        self.assertEqual(a1.attempt_number, 1)

        a2 = services.submit_quiz_attempt(
            student=self.student, quiz_id=self.quiz.pk, score=85.0
        )
        self.assertEqual(a2.attempt_number, 2)

    def test_submit_attempt_creates_record(self):
        """Submitting an attempt should persist a QuizAttempt."""
        attempt = services.submit_quiz_attempt(
            student=self.student, quiz_id=self.quiz.pk, score=90.0
        )
        self.assertEqual(attempt.score, 90.0)
        self.assertEqual(attempt.quiz_id, self.quiz.pk)
        self.assertEqual(attempt.student_id, self.student.pk)

    def test_get_attempt_count(self):
        """get_attempt_count should return the current number of attempts."""
        from courses.selectors import get_attempt_count
        self.assertEqual(get_attempt_count(self.student, self.quiz), 0)

        services.submit_quiz_attempt(
            student=self.student, quiz_id=self.quiz.pk, score=50.0
        )
        self.assertEqual(get_attempt_count(self.student, self.quiz), 1)

    def test_rate_limit_enforced(self):
        """Submitting more than 10 attempts in 5 minutes should raise."""
        for i in range(10):
            services.submit_quiz_attempt(
                student=self.student, quiz_id=self.quiz.pk, score=float(i * 10)
            )
        with self.assertRaises(RateLimitExceeded):
            services.submit_quiz_attempt(
                student=self.student, quiz_id=self.quiz.pk, score=99.0
            )

    def test_get_best_score(self):
        """get_best_score should return the highest score."""
        from courses.selectors import get_best_score
        services.submit_quiz_attempt(
            student=self.student, quiz_id=self.quiz.pk, score=70.0
        )
        services.submit_quiz_attempt(
            student=self.student, quiz_id=self.quiz.pk, score=95.0
        )
        services.submit_quiz_attempt(
            student=self.student, quiz_id=self.quiz.pk, score=80.0
        )
        self.assertEqual(get_best_score(self.student, self.quiz), 95.0)

    def test_unenrolled_student_cannot_submit(self):
        """A student not enrolled should get PermissionDenied."""
        other = User.objects.create_user(
            username="other_q", email="oq@grow.io", password="pass", role="student"
        )
        with self.assertRaises(PermissionDenied):
            services.submit_quiz_attempt(
                student=other, quiz_id=self.quiz.pk, score=60.0
            )
