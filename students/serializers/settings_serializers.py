from rest_framework import serializers


class StudentSettingsSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    email = serializers.EmailField()
    school = serializers.CharField(allow_null=True)
    student_id = serializers.CharField()
    grade = serializers.CharField(allow_null=True)
    total_xp = serializers.IntegerField()
    courses_count = serializers.IntegerField()
