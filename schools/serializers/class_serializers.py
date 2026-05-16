from rest_framework import serializers


class ClassDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    grade_name = serializers.CharField()
    grade_level = serializers.IntegerField()
    school_name = serializers.CharField()
    student_count = serializers.IntegerField()
    teacher_count = serializers.IntegerField()
    active_students = serializers.IntegerField()
    top_performance = serializers.ListField(child=serializers.DictField())
    assigned_teachers = serializers.ListField(child=serializers.DictField())
