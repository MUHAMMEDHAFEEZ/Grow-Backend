from rest_framework import serializers


class TodaysTaskSerializer(serializers.Serializer):
    title = serializers.CharField()
    subject = serializers.CharField(allow_null=True)
    type = serializers.CharField()
    time_remaining = serializers.CharField(allow_null=True)
    xp_reward = serializers.IntegerField()
    status = serializers.CharField()


class DailyMasterSerializer(serializers.Serializer):
    tasks_total = serializers.IntegerField()
    tasks_completed = serializers.IntegerField()
    completion_percentage = serializers.IntegerField()
    level = serializers.IntegerField()


class LeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    username = serializers.CharField()
    total_xp = serializers.IntegerField()


class DashboardSerializer(serializers.Serializer):
    total_xp = serializers.IntegerField()
    daily_streak = serializers.IntegerField()
    todays_tasks = TodaysTaskSerializer(many=True)
    daily_master = DailyMasterSerializer()
    leaderboard = LeaderboardEntrySerializer(many=True)
