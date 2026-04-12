"""
attendance/tests.py — Service-layer tests for attendance marking logic.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.events import EventBus
from core.exceptions import NotFound, PermissionDenied
from courses import services as course_services
from attendance import services
from attendance.models import AttendanceRecord

User = get_user_model()


class AttendanceServiceTest(TestCase):
    def setUp(self):
        EventBus.clear()
        self.teacher = User.objects.create_user(
            username="teacher1", email="t1@grow.io", password="pass", role="teacher"
        )
        self.other_teacher = User.objects.create_user(
            username="teacher2", email="t2@grow.io", password="pass", role="teacher"
        )
        self.student1 = User.objects.create_user(
            username="student1", email="s1@grow.io", password="pass", role="student"
        )
        self.student2 = User.objects.create_user(
            username="student2", email="s2@grow.io", password="pass", role="student"
        )
        self.course = course_services.create_course(teacher=self.teacher, title="History")
        self.date = datetime.date(2026, 4, 10)

    def _records(self):
        return [
            {"student_id": self.student1.pk, "status": "present"},
            {"student_id": self.student2.pk, "status": "absent"},
        ]

    def test_mark_attendance_batch(self):
        result = services.mark_attendance(
            teacher=self.teacher, course_id=self.course.pk,
            date=self.date, records=self._records(),
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(
            AttendanceRecord.objects.filter(course=self.course, date=self.date).count(), 2
        )

    def test_upsert_behaviour(self):
        services.mark_attendance(
            teacher=self.teacher, course_id=self.course.pk,
            date=self.date, records=[{"student_id": self.student1.pk, "status": "present"}],
        )
        services.mark_attendance(
            teacher=self.teacher, course_id=self.course.pk,
            date=self.date, records=[{"student_id": self.student1.pk, "status": "late"}],
        )
        # Should still be exactly one record, updated to "late"
        records = AttendanceRecord.objects.filter(
            course=self.course, student=self.student1, date=self.date
        )
        self.assertEqual(records.count(), 1)
        self.assertEqual(records.first().status, "late")

    def test_absent_emits_event(self):
        received = []
        EventBus.subscribe("attendance_marked", lambda p: received.append(p))
        services.mark_attendance(
            teacher=self.teacher, course_id=self.course.pk,
            date=self.date,
            records=[{"student_id": self.student2.pk, "status": "absent"}],
        )
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["student_id"], self.student2.pk)
        self.assertEqual(received[0]["status"], "absent")

    def test_present_no_event(self):
        received = []
        EventBus.subscribe("attendance_marked", lambda p: received.append(p))
        services.mark_attendance(
            teacher=self.teacher, course_id=self.course.pk,
            date=self.date,
            records=[{"student_id": self.student1.pk, "status": "present"}],
        )
        self.assertEqual(len(received), 0)

    def test_non_teacher_raises(self):
        with self.assertRaises(PermissionDenied):
            services.mark_attendance(
                teacher=self.student1, course_id=self.course.pk,
                date=self.date, records=[],
            )

    def test_unowned_course_raises(self):
        with self.assertRaises(NotFound):
            services.mark_attendance(
                teacher=self.other_teacher, course_id=self.course.pk,
                date=self.date, records=[],
            )
