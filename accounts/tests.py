"""
accounts/tests.py — Tests for auth, profile, password, and school admin flows.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import PasswordResetToken, School

User = get_user_model()

BASE = "/api/v1/auth"


def _register(client, username, email, password, role):
    return client.post(f"{BASE}/register/", {
        "username": username, "email": email, "password": password, "role": role
    })


def _login(client, email, password):
    return client.post(f"{BASE}/login/", {"email": email, "password": password})


def _auth_client(client, email, password):
    """Return (access_token, refresh_token) after login."""
    resp = _login(client, email, password)
    return resp.data["access"], resp.data["refresh"]


class RegisterTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_student_registration(self):
        resp = _register(self.client, "sara", "sara@test.io", "StrongPass123", "student")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["role"], "student")

    def test_school_admin_registration(self):
        resp = _register(self.client, "admin1", "admin@test.io", "AdminPass123", "school_admin")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["role"], "school_admin")

    def test_duplicate_email_rejected(self):
        _register(self.client, "u1", "dup@test.io", "Pass12345", "student")
        resp = _register(self.client, "u2", "dup@test.io", "Pass12345", "teacher")
        self.assertEqual(resp.status_code, 400)

    def test_invalid_role_rejected(self):
        resp = _register(self.client, "u3", "u3@test.io", "Pass12345", "superadmin")
        self.assertEqual(resp.status_code, 400)

    def test_short_password_rejected(self):
        resp = _register(self.client, "u4", "u4@test.io", "abc", "student")
        self.assertEqual(resp.status_code, 400)


class LoginTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        _register(self.client, "ali", "ali@test.io", "StrongPass123", "student")

    def test_login_returns_tokens(self):
        resp = _login(self.client, "ali@test.io", "StrongPass123")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["user"]["email"], "ali@test.io")

    def test_wrong_password_rejected(self):
        resp = _login(self.client, "ali@test.io", "wrongpass")
        self.assertEqual(resp.status_code, 400)

    def test_unknown_email_rejected(self):
        resp = _login(self.client, "ghost@test.io", "anypass")
        self.assertEqual(resp.status_code, 400)


class LogoutTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        _register(self.client, "bob", "bob@test.io", "StrongPass123", "teacher")

    def test_logout_blacklists_token(self):
        access, refresh = _auth_client(self.client, "bob@test.io", "StrongPass123")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.client.post(f"{BASE}/logout/", {"refresh": refresh})
        self.assertEqual(resp.status_code, 204)

    def test_logout_with_invalid_token(self):
        _register(self.client, "bob2", "bob2@test.io", "StrongPass123", "teacher")
        access, _ = _auth_client(self.client, "bob2@test.io", "StrongPass123")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.client.post(f"{BASE}/logout/", {"refresh": "invalidtoken"})
        self.assertEqual(resp.status_code, 400)

    def test_logout_requires_auth(self):
        resp = self.client.post(f"{BASE}/logout/", {"refresh": "anytoken"})
        self.assertEqual(resp.status_code, 401)


class ForgotResetPasswordTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        _register(self.client, "carol", "carol@test.io", "OldPass123", "teacher")

    def test_forgot_password_always_returns_200(self):
        # Existing email
        resp = self.client.post(f"{BASE}/forgot-password/", {"email": "carol@test.io"})
        self.assertEqual(resp.status_code, 200)

    def test_forgot_password_unknown_email_still_200(self):
        resp = self.client.post(f"{BASE}/forgot-password/", {"email": "nobody@test.io"})
        self.assertEqual(resp.status_code, 200)

    def test_reset_password_success(self):
        # Trigger token creation
        self.client.post(f"{BASE}/forgot-password/", {"email": "carol@test.io"})
        user = User.objects.get(email="carol@test.io")
        token = PasswordResetToken.objects.filter(user=user, is_used=False).last()

        resp = self.client.post(f"{BASE}/reset-password/", {
            "token": str(token.token), "new_password": "NewPass123"
        })
        self.assertEqual(resp.status_code, 200)

        # Old password no longer works
        resp = _login(self.client, "carol@test.io", "OldPass123")
        self.assertEqual(resp.status_code, 400)

        # New password works
        resp = _login(self.client, "carol@test.io", "NewPass123")
        self.assertEqual(resp.status_code, 200)

    def test_reset_token_cannot_be_reused(self):
        self.client.post(f"{BASE}/forgot-password/", {"email": "carol@test.io"})
        user = User.objects.get(email="carol@test.io")
        token = PasswordResetToken.objects.filter(user=user, is_used=False).last()

        self.client.post(f"{BASE}/reset-password/", {
            "token": str(token.token), "new_password": "NewPass123"
        })
        resp = self.client.post(f"{BASE}/reset-password/", {
            "token": str(token.token), "new_password": "AnotherPass123"
        })
        self.assertEqual(resp.status_code, 400)

    def test_reset_with_invalid_token(self):
        resp = self.client.post(f"{BASE}/reset-password/", {
            "token": "00000000-0000-0000-0000-000000000000", "new_password": "NewPass123"
        })
        self.assertEqual(resp.status_code, 400)


class ChangePasswordTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        _register(self.client, "dave", "dave@test.io", "OldPass123", "student")
        access, _ = _auth_client(self.client, "dave@test.io", "OldPass123")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_change_password_success(self):
        resp = self.client.post(f"{BASE}/change-password/", {
            "old_password": "OldPass123", "new_password": "NewPass456"
        })
        self.assertEqual(resp.status_code, 200)
        # New password works
        resp = _login(APIClient(), "dave@test.io", "NewPass456")
        self.assertEqual(resp.status_code, 200)

    def test_wrong_old_password_rejected(self):
        resp = self.client.post(f"{BASE}/change-password/", {
            "old_password": "WrongOld", "new_password": "NewPass456"
        })
        self.assertEqual(resp.status_code, 400)

    def test_change_password_requires_auth(self):
        client = APIClient()
        resp = client.post(f"{BASE}/change-password/", {
            "old_password": "OldPass123", "new_password": "NewPass456"
        })
        self.assertEqual(resp.status_code, 401)


class ProfileTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        _register(self.client, "eve", "eve@test.io", "Pass12345", "teacher")
        access, _ = _auth_client(self.client, "eve@test.io", "Pass12345")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_get_profile(self):
        resp = self.client.get(f"{BASE}/profile/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["email"], "eve@test.io")

    def test_update_profile(self):
        resp = self.client.put(f"{BASE}/profile/", {
            "first_name": "Eve",
            "last_name": "Smith",
            "phone": "+1234567890",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["first_name"], "Eve")
        self.assertEqual(resp.data["phone"], "+1234567890")

    def test_profile_requires_auth(self):
        client = APIClient()
        resp = client.get(f"{BASE}/profile/")
        self.assertEqual(resp.status_code, 401)


class SchoolAdminTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        _register(self.client, "school_admin1", "admin@school.io", "AdminPass123", "school_admin")
        access, _ = _auth_client(self.client, "admin@school.io", "AdminPass123")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_create_school(self):
        resp = self.client.post(f"{BASE}/school/", {"name": "Al-Nour School"})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["name"], "Al-Nour School")
        self.assertIn("slug", resp.data)
        self.assertEqual(resp.data["slug"], "al-nour-school")

    def test_cannot_create_two_schools(self):
        self.client.post(f"{BASE}/school/", {"name": "School One"})
        resp = self.client.post(f"{BASE}/school/", {"name": "School Two"})
        self.assertEqual(resp.status_code, 409)

    def test_get_school(self):
        self.client.post(f"{BASE}/school/", {"name": "My School"})
        resp = self.client.get(f"{BASE}/school/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["name"], "My School")

    def test_non_admin_cannot_access_school_endpoint(self):
        client = APIClient()
        _register(client, "student1", "student1@test.io", "Pass12345", "student")
        access, _ = _auth_client(client, "student1@test.io", "Pass12345")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = client.post(f"{BASE}/school/", {"name": "Fake School"})
        self.assertEqual(resp.status_code, 403)
