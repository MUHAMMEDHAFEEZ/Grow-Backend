"""
courses/tests/test_lesson_attendance.py — Tests for join_lesson and attendance endpoints.
"""

from __future__ import annotations

import datetime

import pytest
from django.utils import timezone


@pytest.fixture
def teacher(django_user_model):
    return django_user_model.objects.create_user(
        username="teacher",
        email="teacher@test.com",
        password="testpass123",
        role="teacher",
    )


@pytest.fixture
def student(django_user_model):
    return django_user_model.objects.create_user(
        username="student",
        email="student@test.com",
        password="testpass123",
        role="student",
    )


@pytest.fixture
def course(teacher):
    from courses.models import Course

    return Course.objects.create(title="Test Course", teacher=teacher)


@pytest.fixture
def enrollment(student, course):
    from courses.models import Enrollment

    return Enrollment.objects.create(course=course, student=student)


@pytest.fixture
def lesson(course):
    from courses.models import Lesson

    start = timezone.now()
    end = start + datetime.timedelta(hours=1)
    return Lesson.objects.create(
        course=course,
        title="Test Lesson",
        content="Test content",
        start_time=start,
        end_time=end,
    )


class TestJoinLesson:
    """Tests for join_lesson service function."""

    def test_join_on_time_returns_present(self, student, enrollment, lesson):
        """Student joining at start time should get 'present' status."""
        from courses.services import join_lesson

        result = join_lesson(lesson_id=lesson.pk, student=student)

        assert result.status == "present"
        assert result.is_new is True

    def test_join_within_grace_period_returns_present(
        self, student, enrollment, course, teacher
    ):
        """Student joining within 10-minute grace period should get 'present'."""
        from courses.services import join_lesson
        from courses.models import Lesson

        start = timezone.now()
        lesson = Lesson.objects.create(
            course=course,
            title="Grace Period Test",
            content="Content",
            start_time=start,
            end_time=start + datetime.timedelta(hours=1),
        )

        result = join_lesson(lesson_id=lesson.pk, student=student)
        assert result.status == "present"

    def test_join_after_grace_returns_late(self, student, enrollment, course, teacher):
        """Student joining after grace period should get 'late'."""
        from courses.services import join_lesson
        from courses.models import Lesson

        start = timezone.now() - datetime.timedelta(minutes=15)
        lesson = Lesson.objects.create(
            course=course,
            title="Late Test",
            content="Content",
            start_time=start,
            end_time=start + datetime.timedelta(hours=1),
        )

        result = join_lesson(lesson_id=lesson.pk, student=student)
        assert result.status == "late"

    def test_join_after_end_returns_absent(self, student, enrollment, course, teacher):
        """Student joining after lesson ends should get 'absent'."""
        from courses.services import join_lesson
        from courses.models import Lesson

        start = timezone.now() - datetime.timedelta(hours=2)
        lesson = Lesson.objects.create(
            course=course,
            title="Ended Lesson",
            content="Content",
            start_time=start,
            end_time=start + datetime.timedelta(hours=1),
        )

        result = join_lesson(lesson_id=lesson.pk, student=student)
        assert result.status == "absent"

    def test_join_before_start_rejected(self, student, enrollment, course, teacher):
        """Student joining before lesson starts should be rejected."""
        from courses.services import join_lesson
        from courses.models import Lesson
        from core.exceptions import ValidationError

        start = timezone.now() + datetime.timedelta(hours=1)
        lesson = Lesson.objects.create(
            course=course,
            title="Future Lesson",
            content="Content",
            start_time=start,
            end_time=start + datetime.timedelta(hours=1),
        )

        with pytest.raises(ValidationError):
            join_lesson(lesson_id=lesson.pk, student=student)

    def test_not_enrolled_rejected(self, student, course, teacher):
        """Student not enrolled in course should be rejected."""
        from courses.services import join_lesson
        from courses.models import Lesson
        from core.exceptions import PermissionDenied

        start = timezone.now()
        lesson = Lesson.objects.create(
            course=course,
            title="Test Lesson",
            content="Content",
            start_time=start,
            end_time=start + datetime.timedelta(hours=1),
        )

        with pytest.raises(PermissionDenied):
            join_lesson(lesson_id=lesson.pk, student=student)

    def test_lesson_not_found(self, student):
        """Joining non-existent lesson should raise NotFound."""
        from courses.services import join_lesson
        from core.exceptions import NotFound

        with pytest.raises(NotFound):
            join_lesson(lesson_id=99999, student=student)

    def test_duplicate_join_returns_same_status(self, student, enrollment, lesson):
        """Second join should return same status without creating duplicate."""
        from courses.services import join_lesson
        from attendance.models import AttendanceRecord

        result1 = join_lesson(lesson_id=lesson.pk, student=student)
        assert result1.is_new is True

        result2 = join_lesson(lesson_id=lesson.pk, student=student)
        assert result2.is_new is False
        assert result2.status == result1.status

        count = AttendanceRecord.objects.filter(
            course=lesson.course,
            student=student,
            date=lesson.start_time.date(),
        ).count()
        assert count == 1


class TestGetLessonAttendanceSummary:
    """Tests for get_lesson_attendance_summary service function."""

    def test_teacher_can_view_attendance(
        self, teacher, student, course, enrollment, lesson
    ):
        """Teacher should be able to view lesson attendance."""
        from courses.services import get_lesson_attendance_summary, join_lesson

        join_lesson(lesson_id=lesson.pk, student=student)

        summary = get_lesson_attendance_summary(lesson_id=lesson.pk, teacher=teacher)

        assert summary.lesson_id == lesson.pk
        assert summary.lesson_title == lesson.title
        assert summary.total_enrolled == 1
        assert len(summary.attendance) == 1
        assert summary.attendance[0]["student_id"] == student.pk
        assert summary.attendance[0]["status"] == "present"

    def test_non_teacher_rejected(self, student, enrollment, lesson, django_user_model):
        """Non-teacher should be rejected from viewing attendance."""
        from courses.services import get_lesson_attendance_summary
        from core.exceptions import PermissionDenied

        other_student = django_user_model.objects.create_user(
            username="other",
            email="other@test.com",
            password="testpass123",
            role="student",
        )

        with pytest.raises(PermissionDenied):
            get_lesson_attendance_summary(lesson_id=lesson.pk, teacher=other_student)

    def test_shows_students_without_attendance(
        self, teacher, student, course, enrollment, lesson
    ):
        """Students without attendance should show null status."""
        from courses.services import get_lesson_attendance_summary

        summary = get_lesson_attendance_summary(lesson_id=lesson.pk, teacher=teacher)

        assert summary.total_enrolled == 1
        assert summary.attendance[0]["status"] is None
