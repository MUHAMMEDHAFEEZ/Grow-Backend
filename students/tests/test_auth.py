from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from schools.models import Class, Grade, RegistrationCode, School
from students.models import Student

User = get_user_model()


class StudentAuthTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.school = School.objects.create(name="Test School", school_code="TS", school_type="arabic")
        self.grade = Grade.objects.create(name="Grade 5", level=5, school=self.school)
        self.reg_code = RegistrationCode.objects.create(
            code="STU-2024-G5-001",
            school=self.school,
            grade=self.grade,
            code_type="student",
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
        Student.objects.create(
            user=user,
            full_name="Test Student",
            school=self.school,
            grade=self.grade,
        )

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
        Student.objects.create(
            user=user,
            full_name="Test Student",
            school=self.school,
            grade=self.grade,
        )

        resp = self.client.post("/api/v1/auth/student/login/", {
            "school_id": self.school.id,
            "email": "student2@test.com",
            "password": "wrongpassword",
        })
        self.assertEqual(resp.status_code, 400)


class StudentSignupClassAssignmentTest(TestCase):
    """T027-T029: Student signup auto-assigns class and rejects invalid codes."""

    def setUp(self):
        self.client = APIClient()
        self.school = School.objects.create(name="Test School", school_code="TS", school_type="arabic")
        self.grade = Grade.objects.create(name="Grade 5", level=5, school=self.school)
        self.reg_code = RegistrationCode.objects.create(
            code="CLS-STU-001",
            school=self.school,
            grade=self.grade,
            code_type="student",
        )

    def test_signup_assigns_class(self):
        resp = self.client.post("/api/v1/auth/student/signup/", {
            "school_id": self.school.id,
            "full_name": "Class Test",
            "email": "classtest@example.com",
            "password": "testpass123",
            "student_code": "CLS-STU-001",
        })
        self.assertEqual(resp.status_code, 201)
        student = Student.objects.get(user__email="classtest@example.com")
        self.assertIsNotNone(student.class_fk)
        self.assertEqual(student.class_fk.grade, self.grade)
        self.assertEqual(student.class_fk.school, self.school)

    def test_signup_creates_class_a_for_first_40(self):
        codes = []
        for i in range(2):
            code = RegistrationCode.objects.create(
                code=f"MULTI-STU-{i}",
                school=self.school,
                grade=self.grade,
                code_type="student",
            )
            codes.append(code)

        for i, code in enumerate(codes):
            resp = self.client.post("/api/v1/auth/student/signup/", {
                "school_id": self.school.id,
                "full_name": f"Multi {i}",
                "email": f"multi{i}@example.com",
                "password": "testpass123",
                "student_code": code.code,
            })
            self.assertEqual(resp.status_code, 201)

        class_a = Class.objects.filter(school=self.school, grade=self.grade).first()
        self.assertIsNotNone(class_a)
        self.assertEqual(class_a.students.count(), 2)

    def test_signup_rejects_used_code(self):
        self.client.post("/api/v1/auth/student/signup/", {
            "school_id": self.school.id,
            "full_name": "First User",
            "email": "first@example.com",
            "password": "testpass123",
            "student_code": "CLS-STU-001",
        })
        resp = self.client.post("/api/v1/auth/student/signup/", {
            "school_id": self.school.id,
            "full_name": "Second User",
            "email": "second@example.com",
            "password": "testpass123",
            "student_code": "CLS-STU-001",
        })
        self.assertEqual(resp.status_code, 400)

    def test_signup_rejects_wrong_school_code(self):
        other_school = School.objects.create(name="Other School", school_code="OS", school_type="arabic")
        wrong_code = RegistrationCode.objects.create(
            code="WRONG-SCHOOL-001",
            school=other_school,
            grade=self.grade,
            code_type="student",
        )
        resp = self.client.post("/api/v1/auth/student/signup/", {
            "school_id": self.school.id,
            "full_name": "Wrong School",
            "email": "wrongschool@example.com",
            "password": "testpass123",
            "student_code": wrong_code.code,
        })
        self.assertEqual(resp.status_code, 400)

    def test_signup_rejects_wrong_type_code(self):
        teacher_code = RegistrationCode.objects.create(
            code="TEACHER-CODE-001",
            school=self.school,
            grade=self.grade,
            code_type="teacher",
        )
        resp = self.client.post("/api/v1/auth/student/signup/", {
            "school_id": self.school.id,
            "full_name": "Wrong Type",
            "email": "wrongtype@example.com",
            "password": "testpass123",
            "student_code": teacher_code.code,
        })
        self.assertEqual(resp.status_code, 400)
