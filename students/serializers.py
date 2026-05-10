from rest_framework import serializers


class AddStudentSerializer(serializers.Serializer):
    student_id = serializers.CharField(required=True)
    parent_access_code = serializers.CharField(required=True, write_only=True)


class DashboardResponseSerializer(serializers.Serializer):
    welcome = serializers.DictField()
    xp_system = serializers.DictField()
    daily_mastery = serializers.DictField()
    daily_streak = serializers.DictField()
    leaderboard = serializers.DictField()
    today_tasks = serializers.DictField()
    weekly_progress = serializers.DictField()
    upcoming_session = serializers.DictField(allow_null=True)