"""
tasks/tests/test_services.py — Unit tests for task services and handlers.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

from core.events import EventBus, Events
from courses.models import Course, StudentCourse
from tasks.models import StudentTask
from tasks import services as task_services

User = get_user_model()


class TaskServiceTest(TestCase):
    def setUp(self):
        EventBus.clear()
        self.teacher = User.objects.create_user(
            username="t_tasks", email="tt@grow.io", password="pass", role="teacher"
        )
        self.student = User.objects.create_user(
            username="s_tasks", email="st@grow.io", password="pass", role="student"
        )
        self.student2 = User.objects.create_user(
            username="s_tasks2", email="st2@grow.io", password="pass", role="student"
        )
        self.course = Course.objects.create(teacher=self.teacher, title="Task Test Course")
        StudentCourse.objects.create(course=self.course, student=self.student)
        StudentCourse.objects.create(course=self.course, student=self.student2)

    def test_create_tasks_for_content_creates_for_all_students(self):
        count = task_services.create_tasks_for_content(
            student_ids=[self.student.pk, self.student2.pk],
            course_id=self.course.pk,
            content_type="lesson",
            content_id=10,
            title="Algebra Basics",
        )
        self.assertEqual(count, 2)
        self.assertEqual(StudentTask.objects.count(), 2)

    def test_create_tasks_for_content_idempotent(self):
        task_services.create_tasks_for_content(
            student_ids=[self.student.pk],
            course_id=self.course.pk,
            content_type="lesson",
            content_id=10,
            title="Algebra Basics",
        )
        task_services.create_tasks_for_content(
            student_ids=[self.student.pk],
            course_id=self.course.pk,
            content_type="lesson",
            content_id=10,
            title="Algebra Basics",
        )
        self.assertEqual(StudentTask.objects.count(), 1)

    def test_create_tasks_for_content_title_format_lesson(self):
        task_services.create_tasks_for_content(
            student_ids=[self.student.pk],
            course_id=self.course.pk,
            content_type="lesson",
            content_id=1,
            title="Algebra",
        )
        task = StudentTask.objects.first()
        self.assertEqual(task.title, "Study Lesson: Algebra")

    def test_create_tasks_for_content_title_format_quiz(self):
        task_services.create_tasks_for_content(
            student_ids=[self.student.pk],
            course_id=self.course.pk,
            content_type="quiz",
            content_id=1,
            title="Chapter 1",
        )
        task = StudentTask.objects.first()
        self.assertEqual(task.title, "Complete Quiz: Chapter 1")

    def test_create_tasks_for_content_title_format_assignment(self):
        task_services.create_tasks_for_content(
            student_ids=[self.student.pk],
            course_id=self.course.pk,
            content_type="assignment",
            content_id=1,
            title="Week 5 HW",
        )
        task = StudentTask.objects.first()
        self.assertEqual(task.title, "Submit Assignment: Week 5 HW")

    def test_complete_task_marks_as_completed(self):
        task_services.create_tasks_for_content(
            student_ids=[self.student.pk],
            course_id=self.course.pk,
            content_type="lesson",
            content_id=1,
            title="Algebra",
        )
        task = task_services.complete_task(
            student=self.student, content_type="lesson", content_id=1
        )
        self.assertIsNotNone(task)
        self.assertEqual(task.status, StudentTask.Status.COMPLETED)
        self.assertIsNotNone(task.completed_at)

    def test_complete_task_idempotent(self):
        task_services.create_tasks_for_content(
            student_ids=[self.student.pk],
            course_id=self.course.pk,
            content_type="lesson",
            content_id=1,
            title="Algebra",
        )
        task_services.complete_task(
            student=self.student, content_type="lesson", content_id=1
        )
        task_services.complete_task(
            student=self.student, content_type="lesson", content_id=1
        )
        task = StudentTask.objects.get(
            student=self.student, content_type="lesson", content_id=1
        )
        self.assertEqual(task.status, StudentTask.Status.COMPLETED)

    def test_complete_nonexistent_task_returns_none(self):
        task = task_services.complete_task(
            student=self.student, content_type="lesson", content_id=999
        )
        self.assertIsNone(task)

    def test_task_created_as_pending_by_default(self):
        task_services.create_tasks_for_content(
            student_ids=[self.student.pk],
            course_id=self.course.pk,
            content_type="lesson",
            content_id=42,
            title="Test",
        )
        task = StudentTask.objects.first()
        self.assertEqual(task.status, StudentTask.Status.PENDING)

    def test_unique_constraint_enforced(self):
        task_services.create_tasks_for_content(
            student_ids=[self.student.pk],
            course_id=self.course.pk,
            content_type="lesson",
            content_id=1,
            title="Test",
        )
        # Try to create duplicate via model directly (should raise)
        with self.assertRaises(Exception):
            StudentTask.objects.create(
                student=self.student,
                course=self.course,
                content_type="lesson",
                content_id=1,
                title="Duplicate",
            )


class TaskEventHandlersTest(TestCase):
    def setUp(self):
        EventBus.clear()
        self.teacher = User.objects.create_user(
            username="t_evt", email="tev@grow.io", password="pass", role="teacher"
        )
        self.student = User.objects.create_user(
            username="s_evt", email="sev@grow.io", password="pass", role="student"
        )
        self.course = Course.objects.create(teacher=self.teacher, title="Event Course")
        StudentCourse.objects.create(course=self.course, student=self.student)

    def test_lesson_created_event_creates_tasks(self):
        from tasks.handlers import register_handlers
        register_handlers()

        EventBus.publish(
            Events.LESSON_CREATED,
            {
                "lesson_id": 100,
                "course_id": self.course.pk,
                "course_title": self.course.title,
                "lesson_title": "Test Lesson",
            },
        )
        self.assertEqual(StudentTask.objects.count(), 1)
        task = StudentTask.objects.first()
        self.assertEqual(task.content_type, "lesson")
        self.assertEqual(task.content_id, 100)
        self.assertEqual(task.title, "Study Lesson: Test Lesson")

    def test_quiz_created_event_creates_tasks(self):
        from tasks.handlers import register_handlers
        register_handlers()

        EventBus.publish(
            Events.QUIZ_CREATED,
            {
                "quiz_id": 200,
                "course_id": self.course.pk,
                "course_title": self.course.title,
                "quiz_title": "Ch 1 Quiz",
                "max_score": 100.0,
            },
        )
        self.assertEqual(StudentTask.objects.count(), 1)
        task = StudentTask.objects.first()
        self.assertEqual(task.content_type, "quiz")
        self.assertEqual(task.content_id, 200)

    def test_assignment_created_event_creates_tasks(self):
        from tasks.handlers import register_handlers
        register_handlers()

        EventBus.publish(
            Events.ASSIGNMENT_CREATED,
            {
                "assignment_id": 300,
                "course_id": self.course.pk,
                "course_title": self.course.title,
                "title": "Week 1 HW",
                "due_date": "2026-05-14",
                "teacher_id": self.teacher.pk,
            },
        )
        self.assertEqual(StudentTask.objects.count(), 1)
        task = StudentTask.objects.first()
        self.assertEqual(task.content_type, "assignment")
        self.assertEqual(task.content_id, 300)

    def test_lesson_completed_event_completes_task(self):
        from tasks.handlers import register_handlers
        register_handlers()

        StudentTask.objects.create(
            student=self.student,
            course=self.course,
            content_type="lesson",
            content_id=100,
            title="Study Lesson: Test",
        )
        EventBus.publish(
            Events.LESSON_COMPLETED,
            {
                "student_id": self.student.pk,
                "lesson_id": 100,
                "course_id": self.course.pk,
                "course_title": self.course.title,
                "lesson_title": "Test",
                "timestamp": "2026-05-07T12:00:00Z",
            },
        )
        task = StudentTask.objects.first()
        self.assertEqual(task.status, StudentTask.Status.COMPLETED)

    def test_quiz_submitted_event_completes_task(self):
        from tasks.handlers import register_handlers
        register_handlers()

        StudentTask.objects.create(
            student=self.student,
            course=self.course,
            content_type="quiz",
            content_id=200,
            title="Complete Quiz: Ch 1",
        )
        EventBus.publish(
            Events.QUIZ_SUBMITTED,
            {
                "student_id": self.student.pk,
                "quiz_id": 200,
                "course_id": self.course.pk,
                "score": 85.0,
                "attempt_number": 1,
                "timestamp": "2026-05-07T12:00:00Z",
            },
        )
        task = StudentTask.objects.first()
        self.assertEqual(task.status, StudentTask.Status.COMPLETED)

    def test_submission_created_event_completes_assignment_task(self):
        from tasks.handlers import register_handlers
        register_handlers()

        StudentTask.objects.create(
            student=self.student,
            course=self.course,
            content_type="assignment",
            content_id=300,
            title="Submit Assignment: Week 1",
        )
        EventBus.publish(
            Events.SUBMISSION_CREATED,
            {
                "submission_id": 1,
                "assignment_id": 300,
                "student_id": self.student.pk,
                "teacher_id": self.teacher.pk,
                "assignment_title": "Week 1",
                "student_username": self.student.username,
            },
        )
        task = StudentTask.objects.first()
        self.assertEqual(task.status, StudentTask.Status.COMPLETED)

    def test_event_handler_idempotent_on_missing_student(self):
        from tasks.handlers import register_handlers
        register_handlers()
        # Should not crash if student_id in event doesn't exist
        EventBus.publish(
            Events.LESSON_COMPLETED,
            {
                "student_id": 99999,
                "lesson_id": 100,
                "course_id": self.course.pk,
                "course_title": self.course.title,
                "lesson_title": "Test",
                "timestamp": "2026-05-07T12:00:00Z",
            },
        )
        # No assertion needed — just verifying no exception raised
        self.assertTrue(True)
