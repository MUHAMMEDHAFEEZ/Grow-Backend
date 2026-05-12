"""
dashboard/serializers.py — Request/response serialization for dashboard API.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import DashboardInsight, InterventionRecord, StudentNote


class DashboardInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardInsight
        fields = [
            "id",
            "severity",
            "insight_type",
            "title",
            "description",
            "recommendation",
            "is_dismissed",
            "created_at",
        ]
        read_only_fields = fields


class ClassCardSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    teacher = serializers.SerializerMethodField()
    enrollment_count = serializers.IntegerField()
    target_capacity = serializers.IntegerField()
    capacity_utilization = serializers.FloatField()
    average_gpa = serializers.FloatField()
    health_status = serializers.CharField()
    gpa_trend = serializers.CharField()

    @extend_schema_field(serializers.DictField())
    def get_teacher(self, obj):
        return obj.get("teacher", {})


class ClassDetailSerializer(serializers.Serializer):
    class Meta:
        ref_name = "ClassDetail"

    class_info = serializers.DictField(source="class")
    student_distribution = serializers.DictField()
    leaderboard = serializers.ListField()
    gpa_trend_6m = serializers.ListField()
    teacher_performance = serializers.DictField()


class StudentProfileSerializer(serializers.Serializer):
    student = serializers.DictField()
    academic_history = serializers.DictField()
    interventions = serializers.ListField()
    notes = serializers.ListField()


class DashboardOverviewSerializer(serializers.Serializer):
    kpis = serializers.DictField()
    alerts = serializers.ListField()
    charts = serializers.DictField()


class ReportSummarySerializer(serializers.Serializer):
    filters_applied = serializers.DictField()
    summary = serializers.DictField()
    period_comparison = serializers.DictField()
    insights = serializers.ListField()


class RiskSummarySerializer(serializers.Serializer):
    total_at_risk = serializers.IntegerField()
    by_tier = serializers.DictField()
    top_at_risk_students = serializers.ListField()


class StudentNoteSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = StudentNote
        fields = ["id", "author", "note", "created_at", "updated_at"]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    @extend_schema_field(serializers.CharField())
    def get_author(self, obj):
        return obj.author.username if obj.author else "Unknown"


class StudentNoteCreateSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=5000, required=True)

    def validate_note(self, value):
        if not value.strip():
            raise serializers.ValidationError("Note text cannot be empty.")
        return value.strip()


class InterventionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionRecord
        fields = [
            "id",
            "student",
            "action",
            "priority",
            "status",
            "assigned_to",
            "notes",
            "created_at",
            "completed_at",
        ]
        read_only_fields = ["id", "created_at", "completed_at"]
