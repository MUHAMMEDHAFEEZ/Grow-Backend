from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from courses.models import Course
from schools.models import Class, Grade, School
from schools.services.class_service import auto_generate_classes
from students.models import Student

User = get_user_model()


class DashboardSchoolIsolationTest(TestCase):
    """T014-T015: Dashboard overview returns school-scoped counts and is isolated per school."""

    def setUp(self):
        self.client = APIClient()

        self.school_a = School.objects.create(
            name="ELOBOUR", school_code="ELB", school_type="arabic"
        )
        self.school_b = School.objects.create(
            name="ELFOUAD", school_code="ELF", school_type="arabic"
        )

        grade_a_9 = Grade.objects.create(
            name="Grade 9", level=9, stage="secondary", school=self.school_a
        )
        grade_a_10 = Grade.objects.create(
            name="Grade 10", level=10, stage="secondary", school=self.school_a
        )
        grade_b_9 = Grade.objects.create(
            name="Grade 9", level=9, stage="secondary", school=self.school_b
        )

        self.admin_a = User.objects.create_user(
            username="admin_a",
            email="admin_a@test.com",
            password="pass1234",
            role=User.Role.SCHOOL_ADMIN,
        )
        self.admin_b = User.objects.create_user(
            username="admin_b",
            email="admin_b@test.com",
            password="pass1234",
            role=User.Role.SCHOOL_ADMIN,
        )
        self.school_a.admin = self.admin_a
        self.school_a.save(update_fields=["admin"])
        self.school_b.admin = self.admin_b
        self.school_b.save(update_fields=["admin"])

        teacher_user = User.objects.create_user(
            username="teacher_a_1",
            email="teacher_a@test.com",
            password="pass1234",
            role=User.Role.TEACHER,
        )
        self.course_a_9 = Course.objects.create(
            title="Math",
            teacher=teacher_user,
            grade=grade_a_9,
            school=self.school_a,
        )

        other_teacher = User.objects.create_user(
            username="teacher_b_1",
            email="teacher_b@test.com",
            password="pass1234",
            role=User.Role.TEACHER,
        )
        Course.objects.create(
            title="Science",
            teacher=other_teacher,
            grade=grade_b_9,
            school=self.school_b,
        )

        for i in range(5):
            user = User.objects.create_user(
                username=f"studenta_{i}",
                email=f"studenta_{i}@test.com",
                password="pass1234",
                role=User.Role.STUDENT,
            )
            Student.objects.create(
                full_name=f"Student A {i}",
                user=user,
                school=self.school_a,
                grade=grade_a_9,
            )

        for i in range(3):
            user = User.objects.create_user(
                username=f"studentb_{i}",
                email=f"studentb_{i}@test.com",
                password="pass1234",
                role=User.Role.STUDENT,
            )
            Student.objects.create(
                full_name=f"Student B {i}",
                user=user,
                school=self.school_b,
                grade=grade_b_9,
            )

        auto_generate_classes(self.school_a.id)
        auto_generate_classes(self.school_b.id)

    def _get_token(self, user):
        from rest_framework_simplejwt.tokens import RefreshToken
        return str(RefreshToken.for_user(user).access_token)

    def _auth(self, user):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self._get_token(user)}"
        )

    def test_admin_a_sees_correct_counts(self):
        self._auth(self.admin_a)
        resp = self.client.get("/api/v1/dashboard/overview/")
        self.assertEqual(resp.status_code, 200)
        kpis = resp.data["kpis"]
        self.assertEqual(kpis["total_students"], 5)
        self.assertEqual(kpis["total_teachers"], 1)
        self.assertEqual(kpis["total_classes"], 1)

    def test_admin_b_sees_correct_counts(self):
        self._auth(self.admin_b)
        resp = self.client.get("/api/v1/dashboard/overview/")
        self.assertEqual(resp.status_code, 200)
        kpis = resp.data["kpis"]
        self.assertEqual(kpis["total_students"], 3)
        self.assertEqual(kpis["total_teachers"], 1)
        self.assertEqual(kpis["total_classes"], 1)

    def test_admin_a_cannot_see_school_b_data(self):
        self._auth(self.admin_a)
        resp = self.client.get("/api/v1/dashboard/overview/")
        kpis = resp.data["kpis"]
        self.assertNotEqual(kpis["total_students"], 3)
        self.assertNotEqual(kpis["total_students"], 8)

    def test_admin_b_cannot_see_school_a_data(self):
        self._auth(self.admin_b)
        resp = self.client.get("/api/v1/dashboard/overview/")
        kpis = resp.data["kpis"]
        self.assertNotEqual(kpis["total_students"], 5)
        self.assertNotEqual(kpis["total_students"], 8)
