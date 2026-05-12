from rest_framework import serializers


class NotificationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    type = serializers.CharField()
    message = serializers.CharField()
    is_read = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class NotificationReadSerializer(serializers.Serializer):
    message = serializers.CharField(read_only=True)
