from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers
from .models import Submission


class SubmissionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, help_text="Unique submission ID.")
    assignment = serializers.PrimaryKeyRelatedField(
        read_only=True, help_text="ID of the assignment this submission belongs to."
    )
    student = serializers.PrimaryKeyRelatedField(
        read_only=True, help_text="ID of the student who submitted."
    )
    content = serializers.CharField(
        help_text="The student's submitted work (text answer, link, or reference).",
        required=False,
        allow_blank=True,
    )
    status = serializers.ChoiceField(
        choices=Submission.Status.choices,
        read_only=True,
        help_text="Lifecycle status. `pending` = awaiting grade, `graded` = teacher has graded.",
    )
    submitted_at = serializers.DateTimeField(
        read_only=True, help_text="Timestamp when the submission was received."
    )
    file = serializers.FileField(read_only=True, help_text="Uploaded file for this submission.")
    raw_score = serializers.DecimalField(read_only=True, max_digits=5, decimal_places=2, help_text="Raw score given by teacher.")
    normalized_score = serializers.DecimalField(read_only=True, max_digits=5, decimal_places=2, help_text="Normalized score (raw/max * 100).")
    xp_awarded = serializers.IntegerField(read_only=True, help_text="XP awarded for this submission.")
    feedback = serializers.CharField(read_only=True, help_text="Teacher feedback.")
    is_graded = serializers.BooleanField(read_only=True, help_text="Whether this submission has been graded.")

    class Meta:
        model = Submission
        fields = [
            "id", "assignment", "student", "content", "file", "status",
            "raw_score", "normalized_score", "xp_awarded", "feedback",
            "is_graded", "submitted_at",
        ]
        read_only_fields = [
            "id", "assignment", "student", "status", "raw_score",
            "normalized_score", "xp_awarded", "feedback", "is_graded",
            "submitted_at",
        ]


class SubmissionCreateSerializer(serializers.ModelSerializer):
    content = serializers.CharField(
        help_text="The student's answer or work. Plain text, a URL, or structured content.",
        max_length=10000,
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = Submission
        fields = ["content", "file"]


@extend_schema_serializer(component_name="SubmissionGradeSubmissionRequest")
class GradeSubmissionSerializer(serializers.Serializer):
    raw_score = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0)
    feedback = serializers.CharField(required=False, allow_blank=True)


@extend_schema_serializer(component_name="SubmissionTeacherDashboard")
class TeacherDashboardSerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    total_courses = serializers.IntegerField()
    assignments_created = serializers.IntegerField()
    active_assignments = serializers.IntegerField()
    recent_activity = serializers.ListField()
