from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from schools.models import Grade, School
from students.models import Student
from xp.models import XPTransaction

User = get_user_model()


class StudentDashboardTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.school = School.objects.create(name="Test School", school_code="TS", school_type="arabic")
        self.grade = Grade.objects.create(name="Grade 5", level=5, school=self.school)

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

    def authenticate(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_dashboard_returns_data(self):
        self.authenticate()
        resp = self.client.get("/api/v1/student/dashboard/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total_xp", data)
        self.assertIn("daily_streak", data)
        self.assertIn("todays_tasks", data)
        self.assertIn("daily_master", data)
        self.assertIn("leaderboard", data)

    def test_dashboard_unauthorized(self):
        resp = self.client.get("/api/v1/student/dashboard/")
        self.assertEqual(resp.status_code, 401)

    def test_leaderboard_no_datetime_aggregation(self):
        self.authenticate()
        resp = self.client.get("/api/v1/student/dashboard/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("leaderboard", data)
        for entry in data["leaderboard"]:
            self.assertIn("rank", entry)
            self.assertIn("username", entry)
            self.assertIn("total_xp", entry)
            self.assertIsInstance(entry["total_xp"], (int, float))
