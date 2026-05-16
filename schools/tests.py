import re
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from schools.models import Class, Grade, School
from schools.services.class_service import (
    _letter_for_index,
    auto_generate_classes,
    get_or_create_class,
)
from students.models import Student

User = get_user_model()


class AutoGenerateClassesTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="TESTSCHOOL", school_code="TS", school_type="arabic"
        )
        self.grade = Grade.objects.create(
            name="Grade 9", level=9, stage="secondary", school=self.school
        )
        self._offset = 0

    def _make_students(self, count: int, grade=None):
        g = grade or self.grade
        for i in range(count):
            idx = self._offset + i
            user = User.objects.create_user(
                username=f"student_{g.level}_{idx}",
                email=f"student_{g.level}_{idx}@test.com",
                password="pass1234",
                role=User.Role.STUDENT,
            )
            Student.objects.create(
                full_name=f"Student {g.level} {chr(65 + i)}",
                user=user,
                school=self.school,
                grade=g,
            )
        self._offset += count

    def test_35_students_1_class(self):
        self._make_students(35)
        classes = auto_generate_classes(self.school.id)
        self.assertEqual(len(classes), 1)
        self.assertEqual(
            Class.objects.get(id=classes[0].id).students.count(), 35
        )

    def test_60_students_2_classes(self):
        self._make_students(60)
        classes = auto_generate_classes(self.school.id)
        self.assertEqual(len(classes), 2)

    def test_95_students_3_classes(self):
        self._make_students(95)
        classes = auto_generate_classes(self.school.id)
        self.assertEqual(len(classes), 3)

    def test_deterministic_same_input_same_output(self):
        self._make_students(35)
        result1 = auto_generate_classes(self.school.id)
        result2 = auto_generate_classes(self.school.id)
        names1 = [(c.name, c.school_id, c.grade_id) for c in result1]
        names2 = [(c.name, c.school_id, c.grade_id) for c in result2]
        self.assertEqual(names1, names2)

    def test_classes_named_correctly(self):
        self._make_students(105)
        classes = auto_generate_classes(self.school.id)
        names = sorted(c.name for c in classes)
        self.assertEqual(names, ["Class 9 A", "Class 9 B", "Class 9 C"])

    def test_students_assigned_to_class(self):
        self._make_students(35)
        auto_generate_classes(self.school.id)
        class_obj = Class.objects.get(name="Class 9 A")
        students = Student.objects.filter(class_fk=class_obj)
        self.assertEqual(students.count(), 35)


class LetterForIndexTest(TestCase):
    def test_letter_for_index(self):
        self.assertEqual(_letter_for_index(0), "A")
        self.assertEqual(_letter_for_index(1), "B")
        self.assertEqual(_letter_for_index(25), "Z")


class GetOrCreateClassTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="TESTSCHOOL", school_code="TS", school_type="arabic"
        )
        self.grade = Grade.objects.create(
            name="Grade 10", level=10, stage="secondary", school=self.school
        )

    def test_get_or_create_creates_new(self):
        class_obj = get_or_create_class(self.school, self.grade, "A")
        self.assertEqual(class_obj.name, "Class 10 A")
        self.assertEqual(class_obj.school, self.school)
        self.assertEqual(class_obj.grade, self.grade)

    def test_get_or_create_returns_existing(self):
        class_obj1 = get_or_create_class(self.school, self.grade, "A")
        class_obj2 = get_or_create_class(self.school, self.grade, "A")
        self.assertEqual(class_obj1.id, class_obj2.id)


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


class GradeListTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/schools/grades/"

        self.school_a = School.objects.create(name="SCHOOLA", school_code="SA", school_type="arabic")
        self.school_b = School.objects.create(name="SCHOOLB", school_code="SB", school_type="arabic")

        for level in range(1, 13):
            stage = "primary" if level <= 6 else "secondary"
            Grade.objects.create(name=f"Grade {level}", level=level, stage=stage, school=self.school_a)
            Grade.objects.create(name=f"Grade {level}", level=level, stage=stage, school=self.school_b)

    def _results(self, resp):
        return resp.data.get("results", resp.data)

    def test_unauthenticated_returns_global_grades(self):
        self.client.credentials()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        results = self._results(resp)
        for g in results:
            self.assertIn("id", g)
            self.assertIn("name", g)
            self.assertIn("level", g)

    def test_school_id_query_param_returns_scoped_grades(self):
        resp = self.client.get(self.url, {"school_id": self.school_a.id})
        self.assertEqual(resp.status_code, 200)
        results = self._results(resp)
        self.assertEqual(len(results), 12)

    def test_different_schools_return_different_grades(self):
        resp_a = self.client.get(self.url, {"school_id": self.school_a.id})
        resp_b = self.client.get(self.url, {"school_id": self.school_b.id})
        ids_a = [g["id"] for g in self._results(resp_a)]
        ids_b = [g["id"] for g in self._results(resp_b)]
        self.assertNotEqual(ids_a, ids_b)
        self.assertEqual(len(ids_a), 12)
        self.assertEqual(len(ids_b), 12)

    def test_sorted_by_level_ascending(self):
        resp = self.client.get(self.url, {"school_id": self.school_a.id})
        results = self._results(resp)
        levels = [g["level"] for g in results]
        self.assertEqual(levels, list(range(1, 13)))

    def test_no_duplicate_levels(self):
        resp = self.client.get(self.url, {"school_id": self.school_a.id})
        results = self._results(resp)
        levels = [g["level"] for g in results]
        self.assertEqual(len(levels), len(set(levels)))

    def test_name_format_grade_n(self):
        resp = self.client.get(self.url)
        results = self._results(resp)
        for g in results:
            self.assertTrue(re.match(r"^Grade \d+$", g["name"]), f"Unexpected name: {g['name']}")

    def test_response_includes_expected_fields(self):
        resp = self.client.get(self.url)
        results = self._results(resp)
        if results:
            g = results[0]
            self.assertIn("id", g)
            self.assertIn("name", g)
            self.assertIn("level", g)
            self.assertIn("stage", g)
