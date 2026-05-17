from rest_framework import serializers
from .models import Assignment


class AssignmentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, help_text="Unique assignment ID.")
    course = serializers.PrimaryKeyRelatedField(
        read_only=True, help_text="ID of the parent course."
    )
    title = serializers.CharField(help_text="Assignment title.")
    description = serializers.CharField(
        help_text="Full instructions for the assignment.",
        required=False,
    )
    due_date = serializers.DateTimeField(
        help_text="Submission deadline (ISO-8601). Students cannot submit after this time.",
    )
    created_by = serializers.PrimaryKeyRelatedField(
        read_only=True, help_text="Teacher who created the assignment."
    )
    xp_reward = serializers.IntegerField(read_only=True, help_text="XP reward for completing this assignment.")
    late_penalty_xp = serializers.IntegerField(read_only=True, help_text="XP deducted for late submissions.")
    max_score = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True, help_text="Maximum possible score.")
    created_at = serializers.DateTimeField(read_only=True, help_text="Creation timestamp.")
    teacher_file = serializers.FileField(allow_null=True, required=False, help_text="Assignment file uploaded by teacher.")

    class Meta:
        model = Assignment
        fields = [
            "id", "course", "title", "description", "due_date", "created_by",
            "xp_reward", "late_penalty_xp", "max_score", "created_at", "teacher_file",
        ]
        read_only_fields = ["id", "course", "created_by", "xp_reward", "late_penalty_xp", "max_score", "created_at", "teacher_file"]


class AssignmentWriteSerializer(serializers.ModelSerializer):
    title = serializers.CharField(
        max_length=255,
        help_text="Short descriptive title for the assignment.",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Detailed instructions, rubric, or references.",
    )
    due_date = serializers.DateTimeField(
        help_text="Deadline in ISO-8601 format (UTC). Example: 2026-05-01T23:59:00Z",
    )

    class Meta:
        model = Assignment
        fields = ["title", "description", "due_date"]
