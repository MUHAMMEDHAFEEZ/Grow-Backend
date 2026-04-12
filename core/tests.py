"""
core/tests.py — Unit tests for the event bus.
"""
from django.test import TestCase

from core.events import EventBus


class EventBusTest(TestCase):
    def setUp(self):
        EventBus.clear()

    def test_handler_called_on_publish(self):
        results = []
        EventBus.subscribe("test_event", lambda p: results.append(p))
        EventBus.publish("test_event", {"x": 1})
        self.assertEqual(results, [{"x": 1}])

    def test_no_handlers_no_error(self):
        EventBus.publish("unknown_event", {})  # should not raise

    def test_multiple_handlers(self):
        log = []
        EventBus.subscribe("evt", lambda p: log.append("h1"))
        EventBus.subscribe("evt", lambda p: log.append("h2"))
        EventBus.publish("evt", {})
        self.assertEqual(log, ["h1", "h2"])

    def test_handler_exception_does_not_break_others(self):
        log = []

        def bad_handler(p):
            raise RuntimeError("boom")

        EventBus.subscribe("evt", bad_handler)
        EventBus.subscribe("evt", lambda p: log.append("ok"))
        EventBus.publish("evt", {})
        self.assertEqual(log, ["ok"])
