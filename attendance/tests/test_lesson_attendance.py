"""
attendance/tests/test_lesson_attendance.py — Unit tests for attendance service.
"""

from __future__ import annotations

import datetime

import pytest
from django.utils import timezone


class TestCalculateAttendanceStatus:
    """Tests for calculate_attendance_status function."""

    def test_present_within_grace_period(self):
        """Student joins exactly at start time - should be present."""
        from attendance.services import calculate_attendance_status

        start = timezone.now()
        end = start + datetime.timedelta(hours=1)

        result = calculate_attendance_status(
            current_time=start,
            start_time=start,
            end_time=end,
        )
        assert result == "present"

    def test_present_within_grace_period_5_minutes(self):
        """Student joins 5 minutes after start - should be present."""
        from attendance.services import calculate_attendance_status

        start = timezone.now()
        end = start + datetime.timedelta(hours=1)
        current = start + datetime.timedelta(minutes=5)

        result = calculate_attendance_status(
            current_time=current,
            start_time=start,
            end_time=end,
        )
        assert result == "present"

    def test_present_at_grace_period_boundary(self):
        """Student joins exactly at grace period end (10 min) - should be present."""
        from attendance.services import calculate_attendance_status

        start = timezone.now()
        end = start + datetime.timedelta(hours=1)
        current = start + datetime.timedelta(minutes=10)

        result = calculate_attendance_status(
            current_time=current,
            start_time=start,
            end_time=end,
        )
        assert result == "present"

    def test_late_after_grace_period(self):
        """Student joins 11 minutes after start - should be late."""
        from attendance.services import calculate_attendance_status

        start = timezone.now()
        end = start + datetime.timedelta(hours=1)
        current = start + datetime.timedelta(minutes=11)

        result = calculate_attendance_status(
            current_time=current,
            start_time=start,
            end_time=end,
        )
        assert result == "late"

    def test_late_near_end_time(self):
        """Student joins 5 minutes before end - should be late."""
        from attendance.services import calculate_attendance_status

        start = timezone.now()
        end = start + datetime.timedelta(hours=1)
        current = end - datetime.timedelta(minutes=5)

        result = calculate_attendance_status(
            current_time=current,
            start_time=start,
            end_time=end,
        )
        assert result == "late"

    def test_absent_after_end_time(self):
        """Student joins after lesson ends - should be absent."""
        from attendance.services import calculate_attendance_status

        start = timezone.now()
        end = start + datetime.timedelta(hours=1)
        current = end + datetime.timedelta(minutes=5)

        result = calculate_attendance_status(
            current_time=current,
            start_time=start,
            end_time=end,
        )
        assert result == "absent"

    def test_rejected_before_start_time(self):
        """Student joins before lesson starts - should raise ValidationError."""
        from attendance.services import calculate_attendance_status
        from core.exceptions import ValidationError

        start = timezone.now()
        end = start + datetime.timedelta(hours=1)
        current = start - datetime.timedelta(minutes=5)

        with pytest.raises(ValidationError) as exc_info:
            calculate_attendance_status(
                current_time=current,
                start_time=start,
                end_time=end,
            )
        assert "Cannot join lesson before scheduled start time" in str(exc_info.value)


class TestUpsertAttendance:
    """Tests for upsert_attendance function."""

    @pytest.fixture
    def teacher(self, django_user_model):
        return django_user_model.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            role="teacher",
        )

    @pytest.fixture
    def student(self, django_user_model):
        return django_user_model.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            role="student",
        )

    @pytest.fixture
    def course(self, teacher):
        from courses.models import Course

        return Course.objects.create(
            title="Test Course",
            teacher=teacher,
        )

    def test_creates_new_attendance_record(self, student, course):
        """First join should create a new attendance record."""
        from attendance.services import upsert_attendance

        lesson_date = timezone.now().date()
        result = upsert_attendance(
            student=student,
            course=course,
            date=lesson_date,
            status="present",
            lesson_id=1,
        )

        assert result.is_new is True
        assert result.status == "present"
        assert result.date == lesson_date

    def test_updates_existing_attendance_record(self, student, course):
        """Second join should update existing record."""
        from attendance.services import upsert_attendance

        lesson_date = timezone.now().date()

        result1 = upsert_attendance(
            student=student,
            course=course,
            date=lesson_date,
            status="present",
            lesson_id=1,
        )
        assert result1.is_new is True

        result2 = upsert_attendance(
            student=student,
            course=course,
            date=lesson_date,
            status="late",
            lesson_id=1,
        )
        assert result2.is_new is False
        assert result2.status == "late"
