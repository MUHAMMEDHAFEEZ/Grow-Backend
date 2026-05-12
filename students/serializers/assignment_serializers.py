from rest_framework import serializers


class AssignmentDetailSerializer(serializers.Serializer):
    title = serializers.CharField()
    deadline = serializers.DateTimeField()
    xp_reward = serializers.IntegerField(allow_null=True)
    teacher_file_url = serializers.URLField(allow_null=True)
    submission_status = serializers.CharField()


class AssignmentSubmitSerializer(serializers.Serializer):
    file = serializers.FileField()
