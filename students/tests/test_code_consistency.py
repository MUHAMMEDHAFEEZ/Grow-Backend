import uuid

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from schools.models import Grade, RegistrationCode, School as SchoolModel
from students.models import Student

User = get_user_model()


def _unique_email():
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


class TestStudentCodeConsistency(TestCase):
    """Verify the seeded code is preserved as student_id across signup, profile, and dashboard."""

    def setUp(self):
        self.client = APIClient()
        self.school = SchoolModel.objects.create(
            name="TESTSCHOOL", school_code="TS", school_type="arabic"
        )
        self.grade = Grade.objects.create(name="Grade 5", level=5, school=self.school)
        RegistrationCode.objects.create(
            code="STU-2024-G5-001",
            school=self.school,
            grade=self.grade,
            code_type="student",
        )

    def _signup(self, school_id, full_name, email, password, student_code):
        return self.client.post("/api/v1/auth/student/signup/", {
            "school_id": school_id,
            "full_name": full_name,
            "email": email,
            "password": password,
            "student_code": student_code,
        })

    def test_signup_preserves_code(self):
        """US1: Student signs up with a code — student_id must equal the entered code."""
        email = _unique_email()
        resp = self._signup(
            school_id=self.school.id, full_name="Test Student",
            email=email, password="testpass123",
            student_code="STU-2024-G5-001",
        )
        self.assertEqual(resp.status_code, 201)
        student = Student.objects.get(user__email=email)
        self.assertEqual(student.student_id, "STU-2024-G5-001")

    def test_signup_rejects_used_code(self):
        """US4: An already-used code must be rejected."""
        email1 = _unique_email()
        self._signup(
            school_id=self.school.id, full_name="Student One",
            email=email1, password="testpass123",
            student_code="STU-2024-G5-001",
        )
        email2 = _unique_email()
        resp = self._signup(
            school_id=self.school.id, full_name="Student Two",
            email=email2, password="testpass123",
            student_code="STU-2024-G5-001",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid or already used code", str(resp.data))

    def test_signup_rejects_nonexistent_code(self):
        """US5: A non-existent code must be rejected."""
        resp = self._signup(
            school_id=self.school.id, full_name="Test Student",
            email=_unique_email(), password="testpass123",
            student_code="FAKE-CODE-999",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid or already used code", str(resp.data))

    def test_signup_rejects_wrong_school_code(self):
        """Code from school A must not work for school B."""
        other_school = SchoolModel.objects.create(
            name="OTHERSCHOOL", school_code="OS", school_type="arabic"
        )
        RegistrationCode.objects.create(
            code="OTHER-CODE-001",
            school=other_school,
            grade=self.grade,
            code_type="student",
        )
        resp = self._signup(
            school_id=self.school.id, full_name="Test Student",
            email=_unique_email(), password="testpass123",
            student_code="OTHER-CODE-001",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid or already used code", str(resp.data))

    def test_profile_returns_student_id(self):
        """US2: Settings endpoint must return student_id matching the signup code."""
        email = _unique_email()
        self._signup(
            school_id=self.school.id, full_name="Test Student",
            email=email, password="testpass123",
            student_code="STU-2024-G5-001",
        )
        user = User.objects.get(email=email)
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        resp = self.client.get("/api/v1/student/settings/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["student_id"], "STU-2024-G5-001")

    def test_dashboard_returns_student_id(self):
        """US3: School dashboard student list must include student_id field."""
        email = _unique_email()
        self._signup(
            school_id=self.school.id, full_name="Test Student",
            email=email, password="testpass123",
            student_code="STU-2024-G5-001",
        )
        admin = User.objects.create_user(
            username="schooladmin",
            email="admin@TESTSCHOOL.com",
            password="adminpass123",
            role="school_admin",
        )
        refresh = RefreshToken.for_user(admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        resp = self.client.get("/api/v1/schools/students/")
        self.assertEqual(resp.status_code, 200)
        results = resp.data["results"]
        self.assertGreater(len(results), 0)
        self.assertIn("student_id", results[0])
        self.assertEqual(results[0]["student_id"], "STU-2024-G5-001")

    def test_signup_at_different_schools(self):
        """Students at different schools can sign up with their respective codes."""
        school2 = SchoolModel.objects.create(
            name="SCHOOL2", school_code="S2", school_type="arabic"
        )
        grade2 = Grade.objects.create(name="Grade 5", level=5, school=school2)
        RegistrationCode.objects.create(
            code="SCHOOL2-CODE-001",
            school=school2,
            grade=grade2,
            code_type="student",
        )
        email1 = _unique_email()
        resp1 = self._signup(
            school_id=self.school.id, full_name="Student One",
            email=email1, password="testpass123",
            student_code="STU-2024-G5-001",
        )
        self.assertEqual(resp1.status_code, 201)
        student1 = Student.objects.get(user__email=email1)
        self.assertEqual(student1.student_id, "STU-2024-G5-001")

        email2 = _unique_email()
        resp2 = self._signup(
            school_id=school2.id, full_name="Student Two",
            email=email2, password="testpass123",
            student_code="SCHOOL2-CODE-001",
        )
        self.assertEqual(resp2.status_code, 201)
        student2 = Student.objects.get(user__email=email2)
        self.assertEqual(student2.student_id, "SCHOOL2-CODE-001")
