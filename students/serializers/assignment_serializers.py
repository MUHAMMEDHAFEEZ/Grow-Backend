from rest_framework import serializers


class AssignmentDetailSerializer(serializers.Serializer):
    title = serializers.CharField()
    deadline = serializers.DateTimeField()
    xp_reward = serializers.IntegerField(allow_null=True)
    teacher_file_url = serializers.URLField(allow_null=True)
    submission_status = serializers.CharField()
    is_graded = serializers.BooleanField()
    score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    feedback = serializers.CharField(allow_null=True)
    xp_awarded = serializers.IntegerField(allow_null=True)


class AssignmentSubmitSerializer(serializers.Serializer):
    file = serializers.FileField()
