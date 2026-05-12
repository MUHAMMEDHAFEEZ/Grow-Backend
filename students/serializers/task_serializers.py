from rest_framework import serializers


class TaskItemSerializer(serializers.Serializer):
    title = serializers.CharField()
    subject = serializers.CharField(allow_null=True)
    type = serializers.CharField()
    deadline = serializers.DateTimeField()
    xp_reward = serializers.IntegerField()
    status = serializers.CharField()


class MissionItemSerializer(serializers.Serializer):
    title = serializers.CharField()
    subject = serializers.CharField(allow_null=True)
    type = serializers.CharField()
    xp_reward = serializers.IntegerField()
    is_completed = serializers.BooleanField()


class SummaryBarSerializer(serializers.Serializer):
    current_streak = serializers.IntegerField()
    total_xp_today = serializers.IntegerField()
    daily_master_percentage = serializers.IntegerField()


class TasksResponseSerializer(serializers.Serializer):
    past_due = TaskItemSerializer(many=True)
    todays_missions = MissionItemSerializer(many=True)
    summary_bar = SummaryBarSerializer()
