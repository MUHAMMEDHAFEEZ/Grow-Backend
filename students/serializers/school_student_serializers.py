from rest_framework import serializers


class SchoolStudentListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    email = serializers.SerializerMethodField()
    grade_name = serializers.SerializerMethodField()
    grade_level = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    def get_email(self, obj):
        return obj.user.email if obj.user else None

    def get_grade_name(self, obj):
        return obj.grade.name if obj.grade else None

    def get_grade_level(self, obj):
        return obj.grade.level if obj.grade else None
