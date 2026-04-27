from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, min_length=1, max_length=1000)


class ChatResponseSerializer(serializers.Serializer):
    reply = serializers.CharField()