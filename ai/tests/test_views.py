from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from students.models import Student
from schools.models import Grade, School

User = get_user_model()


class ChatViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.school = School.objects.create(name="Test School", school_code="TS", school_type="arabic")
        self.grade = Grade.objects.create(name="Grade 5", level=5, school=self.school)

        self.user = User.objects.create_user(
            username="student1", email="student1@test.com",
            password="testpass123", role="student",
        )
        self.student = Student.objects.create(
            user=self.user,
            full_name="Test Student",
            school=self.school,
            grade=self.grade,
        )

    def _auth(self):
        resp = self.client.post("/api/v1/auth/student/login/", {
            "school_id": self.school.id,
            "email": "student1@test.com",
            "password": "testpass123",
        })
        token = resp.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_unauthenticated_returns_401(self):
        resp = self.client.post("/api/v1/ai/chat/", {"message": "hello"})
        self.assertEqual(resp.status_code, 401)

    def test_non_student_returns_404(self):
        teacher = User.objects.create_user(
            username="teacher1", email="teacher@test.com",
            password="pass", role="teacher",
        )
        self.client.force_authenticate(user=teacher)

        resp = self.client.post("/api/v1/ai/chat/", {"message": "hello"})
        self.assertEqual(resp.status_code, 404)

    def test_missing_message_returns_400(self):
        self._auth()
        resp = self.client.post("/api/v1/ai/chat/", {})
        self.assertEqual(resp.status_code, 400)

    @patch("ai.services.call_ai_api", return_value="AI response")
    def test_successful_chat_returns_200(self, mock_call):
        self._auth()
        resp = self.client.post("/api/v1/ai/chat/", {"message": "help me"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("reply", data)
        self.assertEqual(data["reply"], "AI response")

    @patch("ai.services.call_ai_api", return_value=None)
    def test_fallback_when_api_unavailable(self, mock_call):
        self._auth()
        resp = self.client.post("/api/v1/ai/chat/", {"message": "hello"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("reply", resp.json())
        self.assertIn("Hello", resp.json()["reply"])
