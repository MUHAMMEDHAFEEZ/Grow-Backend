from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from schools.models import Grade, School
from students.models import Student

User = get_user_model()


class SchoolStudentListTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.school_a = School.objects.create(name="SCHOOLA", school_code="SA", school_type="arabic")
        self.school_b = School.objects.create(name="SCHOOLB", school_code="SB", school_type="arabic")

        self.grade_a = Grade.objects.create(name="Grade 5", level=5, school=self.school_a)
        self.grade_b = Grade.objects.create(name="Grade 6", level=6, school=self.school_b)

        self.admin_a = User.objects.create_user(
            username="admin_a",
            email="admin@schoola.edu",
            password="pass1234",
            role=User.Role.SCHOOL_ADMIN,
        )
        self.admin_b = User.objects.create_user(
            username="admin_b",
            email="admin@schoolb.edu",
            password="pass1234",
            role=User.Role.SCHOOL_ADMIN,
        )

        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@schoola.edu",
            password="pass1234",
            role=User.Role.TEACHER,
        )
        self.student_user = User.objects.create_user(
            username="student1",
            email="student@schoola.edu",
            password="pass1234",
            role=User.Role.STUDENT,
        )

        self.student_record = Student.objects.create(
            full_name="Student One",
            user=self.student_user,
            school=self.school_a,
            grade=self.grade_a,
        )
        student_two_user = User.objects.create_user(
            username="student2",
            email="student2@schoola.edu",
            password="pass1234",
            role=User.Role.STUDENT,
        )
        Student.objects.create(
            full_name="Student Two",
            user=student_two_user,
            school=self.school_a,
            grade=self.grade_a,
        )
        other_user = User.objects.create_user(
            username="otherstudent",
            email="other@schoolb.edu",
            password="pass1234",
            role=User.Role.STUDENT,
        )
        Student.objects.create(
            full_name="Other School Student",
            user=other_user,
            school=self.school_b,
            grade=self.grade_b,
        )

    def _auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._get_token(user)}")

    def _get_token(self, user):
        from rest_framework_simplejwt.tokens import RefreshToken
        return str(RefreshToken.for_user(user).access_token)

    def test_admin_lists_students_in_their_school(self):
        self._auth(self.admin_a)
        resp = self.client.get("/api/v1/schools/students/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 2)

    def test_admin_cannot_see_other_school_students(self):
        self._auth(self.admin_b)
        resp = self.client.get("/api/v1/schools/students/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["full_name"], "Other School Student")

    def test_non_admin_gets_403(self):
        self._auth(self.teacher)
        resp = self.client.get("/api/v1/schools/students/")
        self.assertEqual(resp.status_code, 403)

    def test_student_role_gets_403(self):
        self._auth(self.student_user)
        resp = self.client.get("/api/v1/schools/students/")
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_gets_401(self):
        self.client.credentials()
        resp = self.client.get("/api/v1/schools/students/")
        self.assertEqual(resp.status_code, 401)

    def test_empty_school_returns_empty_list(self):
        School.objects.create(name="SCHOOLC", school_code="SC", school_type="arabic")
        admin_c = User.objects.create_user(
            username="admin_c",
            email="admin@schoolc.edu",
            password="pass1234",
            role=User.Role.SCHOOL_ADMIN,
        )
        self._auth(admin_c)
        resp = self.client.get("/api/v1/schools/students/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 0)
        self.assertEqual(resp.data["results"], [])

    def test_response_includes_all_required_fields(self):
        self._auth(self.admin_a)
        resp = self.client.get("/api/v1/schools/students/")
        student = resp.data["results"][0]
        self.assertIn("id", student)
        self.assertIn("full_name", student)
        self.assertIn("email", student)
        self.assertIn("grade_name", student)
        self.assertIn("grade_level", student)
        self.assertIn("created_at", student)

    def test_results_ordered_by_most_recent(self):
        self._auth(self.admin_a)
        resp = self.client.get("/api/v1/schools/students/")
        results = resp.data["results"]
        timestamps = [r["created_at"] for r in results]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

    def test_grade_name_and_level_are_correct(self):
        self._auth(self.admin_a)
        resp = self.client.get("/api/v1/schools/students/")
        student = resp.data["results"][0]
        self.assertEqual(student["grade_name"], "Grade 5")
        self.assertEqual(student["grade_level"], 5)
