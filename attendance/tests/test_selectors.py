from django.contrib.auth import get_user_model
from django.test import TestCase

from attendance.models import AttendanceRecord
from courses.models import Course

User = get_user_model()


class AttendanceSelectorTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="t_att", email="tatt@grow.io", password="pass", role="teacher"
        )
        self.student = User.objects.create_user(
            username="s_att", email="satt@grow.io", password="pass", role="student"
        )
        self.course = Course.objects.create(
            teacher=self.teacher, title="Attendance Test Course"
        )
        from datetime import date
        self.dates = [
            date(2026, 5, 1),
            date(2026, 5, 2),
            date(2026, 5, 3),
            date(2026, 5, 4),
            date(2026, 5, 5),
        ]
        for d in self.dates:
            AttendanceRecord.objects.create(
                course=self.course,
                student=self.student,
                date=d,
                status="present",
                marked_by=self.teacher,
            )
        AttendanceRecord.objects.create(
            course=self.course,
            student=self.student,
            date=date(2026, 5, 6),
            status="absent",
            marked_by=self.teacher,
        )
        AttendanceRecord.objects.create(
            course=self.course,
            student=self.student,
            date=date(2026, 5, 7),
            status="late",
            marked_by=self.teacher,
        )

    def test_get_attendance_summary(self):
        from datetime import date
        from attendance.selectors import get_attendance_summary
        result = get_attendance_summary(
            self.student.pk,
            from_date=date(2026, 5, 1),
            to_date=date(2026, 5, 7),
        )
        self.assertEqual(result["present"], 5)
        self.assertEqual(result["absent"], 1)
        self.assertEqual(result["late"], 1)

    def test_get_attendance_summary_empty_range(self):
        from datetime import date
        from attendance.selectors import get_attendance_summary
        result = get_attendance_summary(
            self.student.pk,
            from_date=date(2026, 6, 1),
            to_date=date(2026, 6, 30),
        )
        self.assertEqual(result["present"], 0)
        self.assertEqual(result["absent"], 0)
        self.assertEqual(result["late"], 0)

    def test_get_attendance_trend_daily(self):
        from datetime import date
        from attendance.selectors import get_attendance_trend
        trend = get_attendance_trend(
            self.course.pk,
            from_date=date(2026, 5, 1),
            to_date=date(2026, 5, 7),
        )
        self.assertGreater(len(trend), 0)
        statuses = {entry["status"] for entry in trend}
        self.assertIn("present", statuses)
        self.assertIn("absent", statuses)
        self.assertIn("late", statuses)

    def test_get_student_attendance_rate(self):
        from attendance.selectors import get_student_attendance_rate
        rate = get_student_attendance_rate(self.student.pk, self.course.pk)
        self.assertEqual(rate, round(5 / 7 * 100, 2))

    def test_get_student_attendance_rate_no_records(self):
        from attendance.selectors import get_student_attendance_rate
        other_student = User.objects.create_user(
            username="s_noatt", email="snoatt@grow.io", password="pass", role="student"
        )
        rate = get_student_attendance_rate(other_student.pk, self.course.pk)
        self.assertEqual(rate, 0.0)
