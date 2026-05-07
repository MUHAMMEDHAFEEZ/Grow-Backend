from rest_framework import serializers

from .models import StudentTask


class StudentTaskSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    student_id = serializers.IntegerField(read_only=True)
    course_id = serializers.IntegerField(read_only=True)
    content_type = serializers.CharField(read_only=True)
    content_id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = StudentTask
        fields = [
            "id", "student_id", "course_id", "content_type", "content_id",
            "title", "status", "created_at", "completed_at",
        ]
        read_only_fields = fields
