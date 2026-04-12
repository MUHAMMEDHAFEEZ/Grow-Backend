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
        help_text="The student's submitted work (text answer, link, or reference)."
    )
    status = serializers.ChoiceField(
        choices=Submission.Status.choices,
        read_only=True,
        help_text="Lifecycle status. `pending` = awaiting grade, `graded` = teacher has graded.",
    )
    submitted_at = serializers.DateTimeField(
        read_only=True, help_text="Timestamp when the submission was received."
    )

    class Meta:
        model = Submission
        fields = ["id", "assignment", "student", "content", "status", "submitted_at"]
        read_only_fields = ["id", "assignment", "student", "status", "submitted_at"]


class SubmissionCreateSerializer(serializers.ModelSerializer):
    content = serializers.CharField(
        help_text="The student's answer or work. Plain text, a URL, or structured content.",
    )

    class Meta:
        model = Submission
        fields = ["content"]
