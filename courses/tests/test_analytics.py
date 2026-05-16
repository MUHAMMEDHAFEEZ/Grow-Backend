from django.contrib.auth import get_user_model
from django.test import TestCase

from courses.models import CourseProgress
from courses import services

User = get_user_model()


class AnalyticsSelectorTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="t_analytics", email="ta@grow.io", password="pass", role="teacher"
        )
        self.student_a = User.objects.create_user(
            username="s_analytics_a", email="saa@grow.io", password="pass", role="student"
        )
        self.student_b = User.objects.create_user(
            username="s_analytics_b", email="sab@grow.io", password="pass", role="student"
        )
        self.course = services.create_course(
            teacher=self.teacher, title="Analytics Test Course"
        )
        services.enroll_student(course_id=self.course.pk, student=self.student_a)
        services.enroll_student(course_id=self.course.pk, student=self.student_b)

    def test_get_total_study_time(self):
        from courses.selectors import get_total_study_time
        # No progress yet
        self.assertEqual(get_total_study_time(self.student_a), 0)

        # Create some progress
        CourseProgress.objects.create(
            student=self.student_a,
            course=self.course,
            study_time_seconds=3600,
            progress_percentage=50.00,
            completion_status=CourseProgress.CompletionStatus.IN_PROGRESS,
        )
        self.assertEqual(get_total_study_time(self.student_a), 3600)

    def test_get_course_completion_rate(self):
        from courses.selectors import get_course_completion_rate
        # No engaged students
        self.assertEqual(get_course_completion_rate(self.course), 0.0)

        # Student A completed
        CourseProgress.objects.create(
            student=self.student_a,
            course=self.course,
            progress_percentage=100.00,
            study_time_seconds=7200,
            completion_status=CourseProgress.CompletionStatus.COMPLETED,
        )
        # Student B in progress
        CourseProgress.objects.create(
            student=self.student_b,
            course=self.course,
            progress_percentage=50.00,
            study_time_seconds=3600,
            completion_status=CourseProgress.CompletionStatus.IN_PROGRESS,
        )
        # 1 out of 2 engaged students completed = 50%
        self.assertEqual(get_course_completion_rate(self.course), 50.0)

    def test_get_engagement_rate(self):
        from courses.selectors import get_engagement_rate
        # No progress records yet
        self.assertEqual(get_engagement_rate(self.course), 0.0)

        CourseProgress.objects.create(
            student=self.student_a,
            course=self.course,
            study_time_seconds=100,
            completion_status=CourseProgress.CompletionStatus.IN_PROGRESS,
        )
        # 1 out of 2 enrolled = 50%
        self.assertEqual(get_engagement_rate(self.course), 50.0)

    def test_get_study_time_trend(self):
        from courses.selectors import get_study_time_trend
        from django.utils import timezone

        CourseProgress.objects.create(
            student=self.student_a,
            course=self.course,
            study_time_seconds=1800,
            last_activity=timezone.now(),
            completion_status=CourseProgress.CompletionStatus.IN_PROGRESS,
        )
        trend = get_study_time_trend(self.student_a, interval="daily")
        self.assertEqual(len(trend), 1)
        self.assertIn("date", trend[0])
        self.assertEqual(trend[0]["study_time_seconds"], 1800)
