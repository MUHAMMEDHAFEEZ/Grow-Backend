"""
courses/tests.py — Unit tests for course services.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model

from core.events import EventBus
from core.exceptions import Conflict, PermissionDenied, NotFound
from courses.models import Course, Enrollment
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
        enrollment = services.enroll_student(course_id=course.pk, student=self.student)
        self.assertEqual(enrollment.student, self.student)

    def test_enroll_duplicate_raises(self):
        course = services.create_course(teacher=self.teacher, title="History")
        services.enroll_student(course_id=course.pk, student=self.student)
        with self.assertRaises(Conflict):
            services.enroll_student(course_id=course.pk, student=self.student)

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
