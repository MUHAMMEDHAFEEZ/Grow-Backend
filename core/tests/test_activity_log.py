from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.models import ActivityLog

User = get_user_model()


class ActivityLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="loguser", email="lu@grow.io", password="pass", role="teacher"
        )

    def test_log_event_creates_record(self):
        from core.services import log_event
        entry = log_event(
            actor=self.user,
            event_type="course_opened",
            target_id=1,
            target_type="Course",
            metadata={"course_title": "Math"},
        )
        self.assertEqual(entry.actor, self.user)
        self.assertEqual(entry.event_type, "course_opened")
        self.assertEqual(entry.target_id, 1)
        self.assertEqual(entry.target_type, "Course")
        self.assertEqual(entry.metadata, {"course_title": "Math"})

    def test_log_event_minimal(self):
        from core.services import log_event
        entry = log_event(
            actor=self.user,
            event_type="login",
        )
        self.assertIsNone(entry.target_id)
        self.assertIsNone(entry.target_type)
        self.assertIsNone(entry.metadata)

    def test_prune_old_logs(self):
        from core.services import log_event, prune_old_logs

        log_event(actor=self.user, event_type="login")
        old_entry = ActivityLog.objects.create(
            actor=self.user,
            event_type="login",
        )
        ActivityLog.objects.filter(pk=old_entry.pk).update(
            created_at=timezone.now() - timedelta(days=400)
        )
        deleted = prune_old_logs()
        self.assertEqual(deleted, 1)
        remaining = ActivityLog.objects.count()
        self.assertEqual(remaining, 1)

    def test_get_logs_filter_by_event_type(self):
        from core.services import log_event
        from core.selectors import get_logs

        log_event(actor=self.user, event_type="login")
        log_event(actor=self.user, event_type="course_opened", target_id=1, target_type="Course")
        log_event(actor=self.user, event_type="course_opened", target_id=2, target_type="Course")

        results = list(get_logs(event_type="course_opened"))
        self.assertEqual(len(results), 2)

    def test_get_logs_filter_by_actor(self):
        from core.services import log_event
        from core.selectors import get_logs

        other = User.objects.create_user(
            username="otherlog", email="ol@grow.io", password="pass", role="student"
        )
        log_event(actor=self.user, event_type="login")
        log_event(actor=other, event_type="login")

        results = list(get_logs(actor_id=self.user.pk))
        self.assertEqual(len(results), 1)

    def test_get_logs_limit(self):
        from core.services import log_event
        from core.selectors import get_logs

        for i in range(10):
            log_event(actor=self.user, event_type="login")

        results = list(get_logs(limit=3))
        self.assertEqual(len(results), 3)
