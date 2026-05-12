from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from students.models import Student, School, Grade

User = get_user_model()


class StudentAuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(name="Test School")
        self.grade = Grade.objects.create(name="Grade 5", level=5)
        self.student = Student.objects.create(
            full_name="Test Student",
            student_id="STU-2024-G5-001",
            generated_password="STU-2024-G5-001",
            school=self.school,
            grade=self.grade,
        )

    def test_signup_valid_code(self):
        resp = self.client.post("/api/v1/auth/student/signup/", {
            "school_id": self.school.id,
            "full_name": "Test Student",
            "email": "test@example.com",
            "password": "testpass123",
            "student_code": "STU-2024-G5-001",
        })
        self.assertEqual(resp.status_code, 201)
        self.assertIn("access", resp.json())

    def test_signup_invalid_code(self):
        resp = self.client.post("/api/v1/auth/student/signup/", {
            "school_id": self.school.id,
            "full_name": "Test Student",
            "email": "test@example.com",
            "password": "testpass123",
            "student_code": "INVALID-CODE",
        })
        self.assertEqual(resp.status_code, 400)

    def test_login_success(self):
        user = User.objects.create_user(
            username="student1", email="student@test.com",
            password="testpass123", role="student"
        )
        self.student.user = user
        self.student.save()

        resp = self.client.post("/api/v1/auth/student/login/", {
            "school_id": self.school.id,
            "email": "student@test.com",
            "password": "testpass123",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.json())

    def test_login_wrong_password(self):
        user = User.objects.create_user(
            username="student2", email="student2@test.com",
            password="testpass123", role="student"
        )
        self.student.user = user
        self.student.save()

        resp = self.client.post("/api/v1/auth/student/login/", {
            "school_id": self.school.id,
            "email": "student2@test.com",
            "password": "wrongpassword",
        })
        self.assertEqual(resp.status_code, 400)
