from rest_framework import serializers


class DashboardSerializer(serializers.Serializer):
    gpa = serializers.DictField()
    study_hours = serializers.DictField()
    engagement = serializers.IntegerField()
    subjects = serializers.ListField()
    recent_activity = serializers.ListField()