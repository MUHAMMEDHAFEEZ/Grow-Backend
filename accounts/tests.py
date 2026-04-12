"""
accounts/tests.py — Tests for auth, profile, password, and school admin flows.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import EnrollmentCode, PasswordResetToken, School, SchoolMembership

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


# ── Enrollment Code Helpers ───────────────────────────────────────────────────


def _create_school_with_admin(client, admin_username, admin_email, school_name):
    """Register a school admin, create a school, return (access_token, school_data)."""
    _register(client, admin_username, admin_email, "AdminPass123", "school_admin")
    access, _ = _auth_client(client, admin_email, "AdminPass123")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    resp = client.post(f"{BASE}/school/", {"name": school_name})
    assert resp.status_code == 201, resp.data
    return access, resp.data


def _get_first_available_code(school_slug_or_id):
    """Return the token of the first AVAILABLE enrollment code for a school."""
    code = EnrollmentCode.objects.filter(
        school__name__icontains="",
        status=EnrollmentCode.Status.AVAILABLE,
    ).first()
    return str(code.token) if code else None


def _get_first_available_code_for_school(school_id):
    return EnrollmentCode.objects.filter(
        school_id=school_id, status=EnrollmentCode.Status.AVAILABLE
    ).first()


# ── US3: Auto-generation on School Creation ───────────────────────────────────


class AutoGenerateCodesOnSchoolCreationTest(TestCase):
    """US3: When a school is created, an initial pool of enrollment codes is auto-generated."""

    def setUp(self):
        self.client = APIClient()

    def test_codes_generated_on_school_creation(self):
        _register(self.client, "admin_ag", "ag@test.io", "AdminPass123", "school_admin")
        access, _ = _auth_client(self.client, "ag@test.io", "AdminPass123")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.client.post(f"{BASE}/school/", {"name": "Auto Gen School"})
        self.assertEqual(resp.status_code, 201)

        school = School.objects.get(name="Auto Gen School")
        code_count = EnrollmentCode.objects.filter(school=school).count()
        self.assertGreater(code_count, 0)

    def test_admin_is_auto_enrolled_as_member(self):
        _register(self.client, "admin_enroll", "ae@test.io", "AdminPass123", "school_admin")
        access, _ = _auth_client(self.client, "ae@test.io", "AdminPass123")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        self.client.post(f"{BASE}/school/", {"name": "Admin School"})

        admin = User.objects.get(email="ae@test.io")
        school = School.objects.get(name="Admin School")
        self.assertTrue(
            SchoolMembership.objects.filter(
                user=admin, school=school, role=SchoolMembership.Role.ADMIN
            ).exists()
        )


# ── US1: Use enrollment code to enroll ───────────────────────────────────────


class UseEnrollmentCodeTest(TestCase):
    """US1: Students and teachers can enroll using a valid enrollment code."""

    def setUp(self):
        self.client = APIClient()
        # Create a school with admin
        _register(self.client, "admin_use", "admin_use@test.io", "AdminPass123", "school_admin")
        admin_access, _ = _auth_client(self.client, "admin_use@test.io", "AdminPass123")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_access}")
        resp = self.client.post(f"{BASE}/school/", {"name": "Use Code School"})
        self.school = School.objects.get(name="Use Code School")

        # Register a student
        self.student_client = APIClient()
        _register(self.student_client, "student_use", "student_use@test.io", "StudentPass123", "student")
        s_access, _ = _auth_client(self.student_client, "student_use@test.io", "StudentPass123")
        self.student_client.credentials(HTTP_AUTHORIZATION=f"Bearer {s_access}")

    def _get_code(self):
        return _get_first_available_code_for_school(self.school.pk)

    def test_student_can_use_valid_code(self):
        code = self._get_code()
        self.assertIsNotNone(code)
        resp = self.student_client.post(f"{BASE}/enrollment-codes/use/", {"code": str(code.token)})
        self.assertEqual(resp.status_code, 201)
        self.assertIn("school", resp.data)

    def test_code_is_marked_used_after_enrollment(self):
        code = self._get_code()
        self.student_client.post(f"{BASE}/enrollment-codes/use/", {"code": str(code.token)})
        code.refresh_from_db()
        self.assertEqual(code.status, EnrollmentCode.Status.USED)

    def test_used_code_cannot_be_reused(self):
        code = self._get_code()
        self.student_client.post(f"{BASE}/enrollment-codes/use/", {"code": str(code.token)})

        # Second student tries to use the same code
        student2_client = APIClient()
        _register(student2_client, "student2_use", "student2_use@test.io", "StudentPass123", "student")
        s2_access, _ = _auth_client(student2_client, "student2_use@test.io", "StudentPass123")
        student2_client.credentials(HTTP_AUTHORIZATION=f"Bearer {s2_access}")
        resp = student2_client.post(f"{BASE}/enrollment-codes/use/", {"code": str(code.token)})
        self.assertEqual(resp.status_code, 400)

    def test_invalid_uuid_format_rejected(self):
        resp = self.student_client.post(f"{BASE}/enrollment-codes/use/", {"code": "not-a-uuid"})
        self.assertEqual(resp.status_code, 400)

    def test_already_member_cannot_re_enroll(self):
        code = self._get_code()
        self.student_client.post(f"{BASE}/enrollment-codes/use/", {"code": str(code.token)})
        code2 = _get_first_available_code_for_school(self.school.pk)
        if code2:
            resp = self.student_client.post(f"{BASE}/enrollment-codes/use/", {"code": str(code2.token)})
            self.assertEqual(resp.status_code, 400)

    def test_unauthenticated_cannot_use_code(self):
        code = self._get_code()
        client = APIClient()
        resp = client.post(f"{BASE}/enrollment-codes/use/", {"code": str(code.token)})
        self.assertEqual(resp.status_code, 401)

    def test_nonexistent_code_rejected(self):
        resp = self.student_client.post(
            f"{BASE}/enrollment-codes/use/",
            {"code": "00000000-0000-0000-0000-000000000000"},
        )
        self.assertEqual(resp.status_code, 400)


# ── US2: Teacher one-school restriction ──────────────────────────────────────


class TeacherOneSchoolRestrictionTest(TestCase):
    """US2: Teachers can only belong to one school at a time."""

    def setUp(self):
        self.client = APIClient()

        # School A
        _register(self.client, "admin_a", "admin_a@test.io", "AdminPass123", "school_admin")
        a_access, _ = _auth_client(self.client, "admin_a@test.io", "AdminPass123")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {a_access}")
        self.client.post(f"{BASE}/school/", {"name": "School A"})
        self.school_a = School.objects.get(name="School A")

        # School B (different admin)
        client_b = APIClient()
        _register(client_b, "admin_b", "admin_b@test.io", "AdminPass123", "school_admin")
        b_access, _ = _auth_client(client_b, "admin_b@test.io", "AdminPass123")
        client_b.credentials(HTTP_AUTHORIZATION=f"Bearer {b_access}")
        client_b.post(f"{BASE}/school/", {"name": "School B"})
        self.school_b = School.objects.get(name="School B")

        # Teacher
        self.teacher_client = APIClient()
        _register(self.teacher_client, "teacher_one", "teacher_one@test.io", "TeachPass123", "teacher")
        t_access, _ = _auth_client(self.teacher_client, "teacher_one@test.io", "TeachPass123")
        self.teacher_client.credentials(HTTP_AUTHORIZATION=f"Bearer {t_access}")

    def test_teacher_can_join_first_school(self):
        code = _get_first_available_code_for_school(self.school_a.pk)
        self.assertIsNotNone(code)
        resp = self.teacher_client.post(f"{BASE}/enrollment-codes/use/", {"code": str(code.token)})
        self.assertEqual(resp.status_code, 201)

    def test_teacher_blocked_from_joining_second_school(self):
        code_a = _get_first_available_code_for_school(self.school_a.pk)
        self.teacher_client.post(f"{BASE}/enrollment-codes/use/", {"code": str(code_a.token)})

        code_b = _get_first_available_code_for_school(self.school_b.pk)
        self.assertIsNotNone(code_b)
        resp = self.teacher_client.post(f"{BASE}/enrollment-codes/use/", {"code": str(code_b.token)})
        self.assertEqual(resp.status_code, 400)

    def test_student_can_join_multiple_schools(self):
        """Students are not restricted to one school."""
        student_client = APIClient()
        _register(student_client, "student_multi", "student_multi@test.io", "SPass123", "student")
        s_access, _ = _auth_client(student_client, "student_multi@test.io", "SPass123")
        student_client.credentials(HTTP_AUTHORIZATION=f"Bearer {s_access}")

        code_a = _get_first_available_code_for_school(self.school_a.pk)
        resp_a = student_client.post(f"{BASE}/enrollment-codes/use/", {"code": str(code_a.token)})
        self.assertEqual(resp_a.status_code, 201)

        code_b = _get_first_available_code_for_school(self.school_b.pk)
        self.assertIsNotNone(code_b)
        resp_b = student_client.post(f"{BASE}/enrollment-codes/use/", {"code": str(code_b.token)})
        self.assertEqual(resp_b.status_code, 201)


# ── US4: Admin list enrollment codes ─────────────────────────────────────────


class EnrollmentCodeListTest(TestCase):
    """US4: School admins can list all enrollment codes with usage status."""

    def setUp(self):
        self.client = APIClient()
        _register(self.client, "admin_list", "admin_list@test.io", "AdminPass123", "school_admin")
        access, _ = _auth_client(self.client, "admin_list@test.io", "AdminPass123")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.client.post(f"{BASE}/school/", {"name": "List School"})
        self.school_id = resp.data["id"]

    def test_admin_can_list_codes(self):
        resp = self.client.get(f"{BASE}/schools/{self.school_id}/enrollment-codes/")
        self.assertEqual(resp.status_code, 200)
        # Response is paginated: {"count": N, "results": [...]}
        self.assertIn("results", resp.data)
        self.assertGreater(resp.data["count"], 0)

    def test_list_includes_status_field(self):
        resp = self.client.get(f"{BASE}/schools/{self.school_id}/enrollment-codes/")
        self.assertEqual(resp.status_code, 200)
        first = resp.data["results"][0]
        self.assertIn("status", first)
        self.assertIn("token", first)

    def test_non_admin_cannot_list_codes(self):
        student_client = APIClient()
        _register(student_client, "student_list", "student_list@test.io", "SPass123", "student")
        s_access, _ = _auth_client(student_client, "student_list@test.io", "SPass123")
        student_client.credentials(HTTP_AUTHORIZATION=f"Bearer {s_access}")
        resp = student_client.get(f"{BASE}/schools/{self.school_id}/enrollment-codes/")
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_cannot_list_codes(self):
        client = APIClient()
        resp = client.get(f"{BASE}/schools/{self.school_id}/enrollment-codes/")
        self.assertEqual(resp.status_code, 401)

    def test_admin_cannot_list_other_schools_codes(self):
        """Admin of school A should not see school B's codes."""
        other_client = APIClient()
        _register(other_client, "admin_other", "admin_other@test.io", "AdminPass123", "school_admin")
        o_access, _ = _auth_client(other_client, "admin_other@test.io", "AdminPass123")
        other_client.credentials(HTTP_AUTHORIZATION=f"Bearer {o_access}")
        other_client.post(f"{BASE}/school/", {"name": "Other School"})
        other_school = School.objects.get(name="Other School")

        resp = self.client.get(f"{BASE}/schools/{other_school.pk}/enrollment-codes/")
        self.assertEqual(resp.status_code, 403)


# ── US5: Admin generate additional codes & revoke ─────────────────────────────


class GenerateAndRevokeCodesTest(TestCase):
    """US5: School admins can generate additional codes and revoke unused ones."""

    def setUp(self):
        self.client = APIClient()
        _register(self.client, "admin_gen", "admin_gen@test.io", "AdminPass123", "school_admin")
        access, _ = _auth_client(self.client, "admin_gen@test.io", "AdminPass123")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.client.post(f"{BASE}/school/", {"name": "Gen School"})
        self.school_id = resp.data["id"]

    def test_admin_can_generate_additional_codes(self):
        resp = self.client.post(
            f"{BASE}/schools/{self.school_id}/enrollment-codes/generate/",
            {"quantity": 5},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["generated"], 5)
        self.assertEqual(len(resp.data["codes"]), 5)

    def test_generate_zero_codes_rejected(self):
        resp = self.client.post(
            f"{BASE}/schools/{self.school_id}/enrollment-codes/generate/",
            {"quantity": 0},
        )
        self.assertEqual(resp.status_code, 400)

    def test_non_admin_cannot_generate_codes(self):
        student_client = APIClient()
        _register(student_client, "student_gen", "student_gen@test.io", "SPass123", "student")
        s_access, _ = _auth_client(student_client, "student_gen@test.io", "SPass123")
        student_client.credentials(HTTP_AUTHORIZATION=f"Bearer {s_access}")
        resp = student_client.post(
            f"{BASE}/schools/{self.school_id}/enrollment-codes/generate/",
            {"quantity": 5},
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_revoke_available_code(self):
        code = _get_first_available_code_for_school(self.school_id)
        self.assertIsNotNone(code)
        resp = self.client.post(
            f"{BASE}/schools/{self.school_id}/enrollment-codes/{code.pk}/revoke/"
        )
        self.assertEqual(resp.status_code, 200)
        code.refresh_from_db()
        self.assertEqual(code.status, EnrollmentCode.Status.REVOKED)

    def test_revoked_code_cannot_be_used(self):
        code = _get_first_available_code_for_school(self.school_id)
        self.client.post(
            f"{BASE}/schools/{self.school_id}/enrollment-codes/{code.pk}/revoke/"
        )

        student_client = APIClient()
        _register(student_client, "student_rev", "student_rev@test.io", "SPass123", "student")
        s_access, _ = _auth_client(student_client, "student_rev@test.io", "SPass123")
        student_client.credentials(HTTP_AUTHORIZATION=f"Bearer {s_access}")
        resp = student_client.post(f"{BASE}/enrollment-codes/use/", {"code": str(code.token)})
        self.assertEqual(resp.status_code, 400)

    def test_cannot_revoke_used_code(self):
        code = _get_first_available_code_for_school(self.school_id)

        student_client = APIClient()
        _register(student_client, "student_norev", "student_norev@test.io", "SPass123", "student")
        s_access, _ = _auth_client(student_client, "student_norev@test.io", "SPass123")
        student_client.credentials(HTTP_AUTHORIZATION=f"Bearer {s_access}")
        student_client.post(f"{BASE}/enrollment-codes/use/", {"code": str(code.token)})

        resp = self.client.post(
            f"{BASE}/schools/{self.school_id}/enrollment-codes/{code.pk}/revoke/"
        )
        self.assertEqual(resp.status_code, 400)

    def test_cannot_revoke_already_revoked_code(self):
        code = _get_first_available_code_for_school(self.school_id)
        self.client.post(
            f"{BASE}/schools/{self.school_id}/enrollment-codes/{code.pk}/revoke/"
        )
        resp = self.client.post(
            f"{BASE}/schools/{self.school_id}/enrollment-codes/{code.pk}/revoke/"
        )
        self.assertEqual(resp.status_code, 400)

    def test_admin_cannot_revoke_other_schools_codes(self):
        other_client = APIClient()
        _register(other_client, "admin_other2", "admin_other2@test.io", "AdminPass123", "school_admin")
        o_access, _ = _auth_client(other_client, "admin_other2@test.io", "AdminPass123")
        other_client.credentials(HTTP_AUTHORIZATION=f"Bearer {o_access}")
        other_client.post(f"{BASE}/school/", {"name": "Other School 2"})
        other_school = School.objects.get(name="Other School 2")
        other_code = _get_first_available_code_for_school(other_school.pk)

        resp = self.client.post(
            f"{BASE}/schools/{other_school.pk}/enrollment-codes/{other_code.pk}/revoke/"
        )
        self.assertEqual(resp.status_code, 403)
