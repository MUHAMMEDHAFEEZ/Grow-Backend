from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from ai.models import ChatMessage
from ai.services import (
    _fallback_reply,
    _get_full_name,
    _get_system_instruction,
    _serialize_history_for_prompt,
    build_student_context,
    call_ai_api,
    chat_with_student_context,
)

User = get_user_model()


class BuildStudentContextTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="stu1", email="stu1@test.com",
            password="pass", role="student",
        )
        self.student = self.user

    def test_returns_dict_with_no_data(self):
        ctx = build_student_context(self.student)
        self.assertIsInstance(ctx, dict)
        self.assertIn("gpa", ctx)
        self.assertIn("courses", ctx)
        self.assertIn("weak_subjects", ctx)
        self.assertIn("recent_scores", ctx)
        self.assertIn("study_hours", ctx)
        self.assertIn("attendance_rate", ctx)
        self.assertIn("total_xp", ctx)


class GetSystemInstructionTest(TestCase):
    def test_includes_all_context_keys(self):
        ctx = {
            "gpa": 3.5,
            "courses": ["Math", "Science"],
            "weak_subjects": ["History"],
            "recent_scores": [85, 90],
            "study_hours": 10,
            "attendance_rate": 95,
            "total_xp": 500,
        }
        instruction = _get_system_instruction(ctx)
        self.assertIn("3.5", instruction)
        self.assertIn("Math", instruction)
        self.assertIn("History", instruction)
        self.assertIn("95", instruction)
        self.assertIn("500", instruction)

    def test_handles_empty_courses(self):
        ctx = {
            "gpa": 0, "courses": [], "weak_subjects": [],
            "recent_scores": [], "study_hours": 0,
            "attendance_rate": 100, "total_xp": 0,
        }
        instruction = _get_system_instruction(ctx)
        self.assertIn("None", instruction)


class SerializeHistoryForPromptTest(TestCase):
    def test_returns_empty_string_for_empty_list(self):
        self.assertEqual(_serialize_history_for_prompt([]), "")

    def test_formats_messages(self):
        history = [
            ChatMessage(role="user", message="Hello"),
            ChatMessage(role="assistant", message="Hi there"),
        ]
        result = _serialize_history_for_prompt(history)
        self.assertIn("user: Hello", result)
        self.assertIn("assistant: Hi there", result)


class CallApiApiTest(TestCase):
    @override_settings(AI_API_KEY="")
    def test_returns_none_when_key_missing(self):
        result = call_ai_api("sys", "", "hello")
        self.assertIsNone(result)

    @override_settings(AI_API_KEY="fake-key")
    @patch("ai.services.genai_mod")
    def test_returns_text_on_success(self, mock_genai):
        mock_genai.configure.return_value = None
        mock_model = mock_genai.GenerativeModel.return_value
        mock_model.generate_content.return_value.text = "Test reply"

        result = call_ai_api("system instruction", "history", "hello")
        self.assertEqual(result, "Test reply")

    @override_settings(AI_API_KEY="fake-key")
    @patch("ai.services.genai_mod")
    def test_returns_none_on_exception(self, mock_genai):
        mock_genai.GenerativeModel.side_effect = Exception("API error")

        result = call_ai_api("sys", "", "hello")
        self.assertIsNone(result)


class FallbackReplyTest(TestCase):
    def setUp(self):
        self.context = {
            "full_name": "Ahmed",
            "courses": ["Math", "Science", "History"],
        }

    def test_greeting_with_name(self):
        reply = _fallback_reply("hello", self.context)
        self.assertIn("Ahmed", reply)
        self.assertIn("Math", reply)

    def test_greeting_without_name(self):
        reply = _fallback_reply("hi", {"full_name": "", "courses": []})
        self.assertIn("Hello!", reply)

    def test_thanks_reply(self):
        reply = _fallback_reply("thank you", self.context)
        self.assertIn("You're welcome", reply)
        self.assertNotIn("😊", reply)

    def test_default_reply(self):
        reply = _fallback_reply("what is the capital of france?", self.context)
        self.assertIn("help with your studies", reply)


class GetFullNameTest(TestCase):
    def test_returns_empty_on_error(self):
        result = _get_full_name(None)
        self.assertEqual(result, "")


class ChatWithStudentContextTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="stu2", email="stu2@test.com",
            password="pass", role="student", first_name="Testy",
        )
        self.student = self.user

    def test_empty_message_returns_prompt(self):
        result = chat_with_student_context(self.student, "")
        self.assertEqual(result["reply"], "Please ask me a question!")

    def test_blank_message_returns_prompt(self):
        result = chat_with_student_context(self.student, "   ")
        self.assertEqual(result["reply"], "Please ask me a question!")

    @patch("ai.services.call_ai_api", return_value=None)
    def test_fallback_on_api_failure(self, mock_call):
        result = chat_with_student_context(self.student, "hello")
        self.assertIn("Hello", result["reply"])

    @patch("ai.services.call_ai_api", return_value="AI reply text")
    def test_successful_chat_saves_messages(self, mock_call):
        result = chat_with_student_context(self.student, "help me")
        self.assertEqual(result["reply"], "AI reply text")

        messages = ChatMessage.objects.filter(student=self.student).order_by("created_at")
        self.assertEqual(messages.count(), 2)
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(messages[0].message, "help me")
        self.assertEqual(messages[1].role, "assistant")
        self.assertEqual(messages[1].message, "AI reply text")
