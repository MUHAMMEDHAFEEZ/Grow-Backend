from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from core.exceptions import NotFound, ValidationError


class ReorderLessonsTests(TestCase):
    """Tests for POST /api/v1/teacher/courses/{course_id}/lessons/reorder/"""

    def setUp(self):
        self.client = APIClient()
        from django.contrib.auth import get_user_model
        User = get_user_model()

        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher1@test.com",
            password="pass123",
            role=User.Role.TEACHER,
        )
        self.other_teacher = User.objects.create_user(
            username="teacher2",
            email="teacher2@test.com",
            password="pass123",
            role=User.Role.TEACHER,
        )

        from courses.models import Course, Lesson
        self.course = Course.objects.create(
            teacher=self.teacher,
            title="Test Course",
            description="Desc",
        )
        self.other_course = Course.objects.create(
            teacher=self.other_teacher,
            title="Other Course",
            description="Desc",
        )

        self.lesson_a = Lesson.objects.create(
            course=self.course, title="A", content="A", order=0,
        )
        self.lesson_b = Lesson.objects.create(
            course=self.course, title="B", content="B", order=1,
        )
        self.lesson_c = Lesson.objects.create(
            course=self.course, title="C", content="C", order=2,
        )

    def _url(self, course_id: int) -> str:
        return f"/api/v1/teacher/courses/{course_id}/lessons/reorder/"

    def _auth(self):
        self.client.force_authenticate(user=self.teacher)

    # T008: successfully reorder lessons
    def test_successful_reorder(self):
        self._auth()
        ordered_ids = [self.lesson_c.pk, self.lesson_a.pk, self.lesson_b.pk]
        resp = self.client.post(self._url(self.course.pk), {"ordered_ids": ordered_ids}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 3)
        self.assertEqual(resp.data[0]["id"], self.lesson_c.pk)

    # T009: reorder with same order returns 200
    def test_reorder_same_order(self):
        self._auth()
        ordered_ids = [self.lesson_a.pk, self.lesson_b.pk, self.lesson_c.pk]
        resp = self.client.post(self._url(self.course.pk), {"ordered_ids": ordered_ids}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # T010: unauthorized returns 401
    def test_unauthenticated_returns_401(self):
        resp = self.client.post(self._url(self.course.pk), {"ordered_ids": [1, 2, 3]}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # T011: other teacher cannot reorder
    def test_other_teacher_gets_404(self):
        self.client.force_authenticate(user=self.other_teacher)
        resp = self.client.post(self._url(self.course.pk), {"ordered_ids": [1, 2, 3]}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # T012: lesson from another course causes validation error
    def test_lesson_not_in_course_returns_400(self):
        self._auth()
        from courses.models import Lesson
        foreign_lesson = Lesson.objects.create(
            course=self.other_course, title="X", content="X", order=0,
        )
        ordered_ids = [self.lesson_a.pk, foreign_lesson.pk]
        resp = self.client.post(self._url(self.course.pk), {"ordered_ids": ordered_ids}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # T012b: duplicate IDs return 400
    def test_duplicate_ids_returns_400(self):
        self._auth()
        ordered_ids = [self.lesson_a.pk, self.lesson_a.pk, self.lesson_b.pk]
        resp = self.client.post(self._url(self.course.pk), {"ordered_ids": ordered_ids}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # T013: empty ordered_ids returns 400
    def test_partial_list_returns_400(self):
        self._auth()
        resp = self.client.post(
            self._url(self.course.pk),
            {"ordered_ids": [self.lesson_a.pk, self.lesson_b.pk]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_list_returns_400(self):
        self._auth()
        resp = self.client.post(self._url(self.course.pk), {"ordered_ids": []}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # T013b: service raises ValidationError for non-subset
    def test_service_validation_error(self):
        from teachers.services import reorder_lessons
        with self.assertRaises(ValidationError):
            reorder_lessons(
                teacher=self.teacher,
                course_id=self.course.pk,
                ordered_ids=[99999],
            )

    # T013c: service raises NotFound for wrong course
    def test_service_not_found(self):
        from teachers.services import reorder_lessons
        with self.assertRaises(NotFound):
            reorder_lessons(
                teacher=self.teacher,
                course_id=99999,
                ordered_ids=[1],
            )
