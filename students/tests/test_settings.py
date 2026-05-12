from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from students.models import Student, School, Grade

User = get_user_model()


class StudentSettingsTest(TestCase):
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

        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_settings_returns_profile(self):
        resp = self.client.get("/api/v1/student/settings/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["full_name"], "Test Student")
        self.assertEqual(data["student_id"], "STU-2024-G5-001")
        self.assertIn("total_xp", data)
        self.assertIn("courses_count", data)
