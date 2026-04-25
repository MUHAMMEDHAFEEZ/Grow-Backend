from rest_framework import serializers
from study_sessions.models import StudySession


class StudySessionSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = StudySession
        fields = ["id", "student", "started_at", "ended_at", "duration", "xp_earned"]
        read_only_fields = [
            "id",
            "student",
            "started_at",
            "ended_at",
            "duration",
            "xp_earned",
        ]


class SessionStartSerializer(serializers.Serializer):
    """Serializer for starting a session (no input required)."""

    pass


class SessionEndSerializer(serializers.ModelSerializer):
    """Serializer for ending a session (returns updated session)."""

    class Meta:
        model = StudySession
        fields = ["id", "student", "started_at", "ended_at", "duration", "xp_earned"]
        read_only_fields = fields


class SessionTotalSerializer(serializers.Serializer):
    """Serializer for total study time response."""

    total_duration_seconds = serializers.IntegerField()
    total_duration_formatted = serializers.CharField()
    session_count = serializers.IntegerField()
