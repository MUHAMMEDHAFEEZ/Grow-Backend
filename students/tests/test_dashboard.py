from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from students.models import Student, School, Grade
from xp.models import XPTransaction

User = get_user_model()


class StudentDashboardTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(name="Test School")
        self.grade = Grade.objects.create(name="Grade 5", level=5)

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
            grade=self.grade,
        )

        XPTransaction.objects.create(
            student=self.user, xp_amount=100, source="study"
        )

        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_dashboard_returns_data(self):
        resp = self.client.get("/api/v1/student/dashboard/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total_xp", data)
        self.assertIn("daily_streak", data)
        self.assertIn("todays_tasks", data)
        self.assertIn("daily_master", data)
        self.assertIn("leaderboard", data)

    def test_dashboard_unauthorized(self):
        self.client.credentials()
        resp = self.client.get("/api/v1/student/dashboard/")
        self.assertEqual(resp.status_code, 401)
