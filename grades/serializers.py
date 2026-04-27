from rest_framework import serializers
from .models import Grade


class GradeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, help_text="Unique grade record ID.")
    submission = serializers.PrimaryKeyRelatedField(
        read_only=True, help_text="ID of the graded submission."
    )
    score = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Numeric score between 0.00 and 100.00.",
    )
    feedback = serializers.CharField(
        help_text="Optional teacher comment or feedback for the student.",
        allow_blank=True,
    )
    graded_by = serializers.PrimaryKeyRelatedField(
        read_only=True, help_text="ID of the teacher who graded the submission."
    )
    graded_at = serializers.DateTimeField(read_only=True, help_text="Timestamp when the grade was assigned.")

    class Meta:
        model = Grade
        fields = ["id", "submission", "score", "feedback", "graded_by", "graded_at"]
        read_only_fields = ["id", "submission", "graded_by", "graded_at"]


class GradeWriteSerializer(serializers.Serializer):
    score = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        help_text="Score to assign (0.00 – 100.00).",
    )
    feedback = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional written feedback for the student.",
    )


class GPASerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    gpa = serializers.FloatField()
    graded_count = serializers.IntegerField()
