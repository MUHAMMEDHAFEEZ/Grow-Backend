from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

User = get_user_model()


class OAuthViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    # ── Google OAuth ──────────────────────────────────────────────────────────────

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="test-client-id.apps.googleusercontent.com")
    @patch("accounts.services._validate_google_token", return_value="newuser@gmail.com")
    def test_google_oauth_creates_new_user(self, mock_validate):
        resp = self.client.post("/api/v1/auth/oauth/", {
            "provider": "google",
            "access_token": "valid-google-token",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("token", data)
        self.assertIn("user_id", data)
        self.assertTrue(data["is_first_login"])
        self.assertTrue(User.objects.filter(email="newuser@gmail.com").exists())

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="test-client-id.apps.googleusercontent.com")
    @patch("accounts.services._validate_google_token", return_value="existing@test.com")
    def test_google_oauth_logs_existing_user(self, mock_validate):
        User.objects.create_user(
            username="existing", email="existing@test.com",
            password="pass123", role="parent",
        )

        resp = self.client.post("/api/v1/auth/oauth/", {
            "provider": "google",
            "access_token": "valid-google-token",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("token", data)
        self.assertEqual(data["user_id"], User.objects.get(email="existing@test.com").id)

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="test-client-id.apps.googleusercontent.com")
    @patch("accounts.services._validate_google_token", return_value=None)
    def test_google_oauth_invalid_token(self, mock_validate):
        resp = self.client.post("/api/v1/auth/oauth/", {
            "provider": "google",
            "access_token": "bad-token",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid google token", resp.json()["detail"])

    # ── Facebook OAuth ────────────────────────────────────────────────────────────

    @override_settings(FACEBOOK_APP_ID="123456", FACEBOOK_APP_SECRET="abc123secret")
    @patch("accounts.services._validate_facebook_token", return_value="fbuser@gmail.com")
    def test_facebook_oauth_creates_new_user(self, mock_validate):
        resp = self.client.post("/api/v1/auth/oauth/", {
            "provider": "facebook",
            "access_token": "valid-fb-token",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("token", data)
        self.assertTrue(User.objects.filter(email="fbuser@gmail.com").exists())

    @override_settings(FACEBOOK_APP_ID="123456", FACEBOOK_APP_SECRET="abc123secret")
    @patch("accounts.services._validate_facebook_token", return_value=None)
    def test_facebook_oauth_invalid_token(self, mock_validate):
        resp = self.client.post("/api/v1/auth/oauth/", {
            "provider": "facebook",
            "access_token": "bad-token",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid facebook token", resp.json()["detail"])

    # ── Validation ────────────────────────────────────────────────────────────────

    def test_missing_provider(self):
        resp = self.client.post("/api/v1/auth/oauth/", {"access_token": "token"})
        self.assertEqual(resp.status_code, 400)

    def test_invalid_provider(self):
        resp = self.client.post("/api/v1/auth/oauth/", {
            "provider": "twitter",
            "access_token": "token",
        })
        self.assertEqual(resp.status_code, 400)

    def test_missing_access_token(self):
        resp = self.client.post("/api/v1/auth/oauth/", {"provider": "google"})
        self.assertEqual(resp.status_code, 400)
