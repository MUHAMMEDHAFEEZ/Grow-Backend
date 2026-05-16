from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from courses.models import Course
from courses.selectors import get_enrolled_courses
from schools.models import Grade, School
from students.models import Student
from students.selectors import get_courses_for_student

User = get_user_model()


class CourseSchoolIsolationTest(TestCase):
    """T034-T035: Courses are isolated per school."""

    def setUp(self):
        self.school_a = School.objects.create(
            name="SCHOOLA", school_code="SA", school_type="arabic"
        )
        self.school_b = School.objects.create(
            name="SCHOOLB", school_code="SB", school_type="arabic"
        )

        grade_a_9 = Grade.objects.create(
            name="Grade 9", level=9, stage="secondary", school=self.school_a
        )
        grade_b_9 = Grade.objects.create(
            name="Grade 9", level=9, stage="secondary", school=self.school_b
        )

        teacher_a = User.objects.create_user(
            username="teacher_a", email="ta@test.com",
            password="pass1234", role=User.Role.TEACHER,
        )
        teacher_b = User.objects.create_user(
            username="teacher_b", email="tb@test.com",
            password="pass1234", role=User.Role.TEACHER,
        )

        self.course_a = Course.objects.create(
            title="Math A",
            teacher=teacher_a,
            grade=grade_a_9,
            school=self.school_a,
            is_published=True,
        )
        self.course_b = Course.objects.create(
            title="Math B",
            teacher=teacher_b,
            grade=grade_b_9,
            school=self.school_b,
            is_published=True,
        )

        student_a_user = User.objects.create_user(
            username="studenta", email="sa@test.com",
            password="pass1234", role=User.Role.STUDENT,
        )
        self.student_a = Student.objects.create(
            full_name="Student A",
            user=student_a_user,
            school=self.school_a,
            grade=grade_a_9,
        )

        student_b_user = User.objects.create_user(
            username="studentb", email="sb@test.com",
            password="pass1234", role=User.Role.STUDENT,
        )
        self.student_b = Student.objects.create(
            full_name="Student B",
            user=student_b_user,
            school=self.school_b,
            grade=grade_b_9,
        )

    def test_student_a_sees_only_school_a_courses(self):
        courses = get_enrolled_courses(self.student_a.user)
        course_ids = [c.id for c in courses]
        self.assertIn(self.course_a.id, course_ids)
        self.assertNotIn(self.course_b.id, course_ids)

    def test_student_b_sees_only_school_b_courses(self):
        courses = get_enrolled_courses(self.student_b.user)
        course_ids = [c.id for c in courses]
        self.assertIn(self.course_b.id, course_ids)
        self.assertNotIn(self.course_a.id, course_ids)

    def test_student_a_courses_for_student_selector(self):
        courses = get_courses_for_student(self.student_a.user)
        course_ids = [c["id"] for c in courses]
        self.assertIn(self.course_a.id, course_ids)
        self.assertNotIn(self.course_b.id, course_ids)

    def test_student_b_courses_for_student_selector(self):
        courses = get_courses_for_student(self.student_b.user)
        course_ids = [c["id"] for c in courses]
        self.assertIn(self.course_b.id, course_ids)
        self.assertNotIn(self.course_a.id, course_ids)

    def test_same_grade_courses_from_different_schools_isolated(self):
        courses_a = get_enrolled_courses(self.student_a.user)
        courses_b = get_enrolled_courses(self.student_b.user)
        ids_a = {c.id for c in courses_a}
        ids_b = {c.id for c in courses_b}
        self.assertTrue(ids_a.isdisjoint(ids_b))
