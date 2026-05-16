from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from schools.models import Grade, School


@extend_schema_serializer(component_name="SchoolGrade")
class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = ["id", "name", "level", "stage"]


@extend_schema_serializer(component_name="SchoolSchool")
class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ["id", "name", "school_code", "school_type"]


class SchoolLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class SchoolLoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user_id = serializers.IntegerField()
    role = serializers.CharField()
    username = serializers.CharField()
