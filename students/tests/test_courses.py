from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from courses.models import Course, Lesson
from students.models import Student, School, Grade

User = get_user_model()


class StudentCoursesTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.school = School.objects.create(name="Test School")
        self.student_grade = Grade.objects.create(name="Grade 5", level=5, school=self.school)
        self.course_grade = Grade.objects.create(name="Grade 5", level=5, school=None)

        self.user = User.objects.create_user(
            username="student", email="student@test.com",
            password="testpass123", role="student"
        )
        self.student = Student.objects.create(
            user=self.user,
            full_name="Test Student",
            student_id="STU-2024-G5-001",
            generated_password="STU-2024-G5-001",
            school=self.school,
            grade=self.student_grade,
        )

        self.course = Course.objects.create(
            title="Math 101", grade=self.course_grade,
            teacher=User.objects.create_user(
                username="teacher", email="teacher@test.com",
                password="testpass123", role="teacher"
            ),
            is_published=True,
        )

        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_course_list(self):
        resp = self.client.get("/api/v1/student/courses/")
        self.assertEqual(resp.status_code, 200)

    def test_lesson_complete_idempotent(self):
        lesson = Lesson.objects.create(course=self.course, title="Lesson 1", content="...")
        resp1 = self.client.post(f"/api/v1/student/lessons/{lesson.id}/complete/")
        resp2 = self.client.post(f"/api/v1/student/lessons/{lesson.id}/complete/")
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
