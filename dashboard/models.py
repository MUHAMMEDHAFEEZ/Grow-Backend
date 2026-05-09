from django.conf import settings
from django.db import models


class DashboardInsight(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    class InsightType(models.TextChoices):
        OVERCROWDED_CLASS = "overcrowded_class", "Overcrowded Class"
        PERFORMANCE_DROP = "performance_drop", "Performance Drop"
        AT_RISK_STUDENT = "at_risk_student", "At-Risk Student"
        TEACHER_DECLINE = "teacher_decline", "Teacher Performance Decline"
        CAPACITY_LOW = "capacity_low", "Low Capacity Utilization"

    title = models.CharField(max_length=255)
    description = models.TextField()
    severity = models.CharField(max_length=10, choices=Severity.choices)
    insight_type = models.CharField(max_length=30, choices=InsightType.choices)
    recommendation = models.TextField(blank=True)
    is_dismissed = models.BooleanField(default=False)
    dismissed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dismissed_insights",
    )
    dismissed_at = models.DateTimeField(null=True, blank=True)
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["severity", "is_dismissed"]),
            models.Index(fields=["insight_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_severity_display()}: {self.title}"


class StudentNote(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dashboard_notes",
        limit_choices_to={"role": "student"},
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="written_notes",
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["student", "created_at"]),
        ]

    def __str__(self):
        return f"Note({self.student_id}, {self.author_id}, {self.created_at})"


class RecommendedAction(models.TextChoices):
    PARENT_MEETING = "parent_meeting", "Schedule Parent Meeting"
    TUTORING_REFERRAL = "tutoring_referral", "Refer to Tutoring Program"
    COUNSELING_REFERRAL = "counseling_referral", "Refer to Counseling"
    REDUCE_CLASS_LOAD = "reduce_class_load", "Reduce Class Load Next Semester"
    PEER_MENTORING = "peer_mentoring", "Assign Peer Mentor"
    TEACHER_CHECKIN = "teacher_checkin", "Schedule Teacher Check-in"


class InterventionRecord(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interventions",
        limit_choices_to={"role": "student"},
    )
    action = models.CharField(max_length=30, choices=RecommendedAction.choices)
    priority = models.IntegerField(default=1)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PENDING
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assigned_interventions",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["priority", "created_at"]
        indexes = [
            models.Index(fields=["student", "status"]),
        ]

    def __str__(self):
        return f"Intervention({self.student_id}, {self.action}, {self.status})"
