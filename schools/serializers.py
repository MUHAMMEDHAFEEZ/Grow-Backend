from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from schools.models import Grade


@extend_schema_serializer(component_name="SchoolGrade")
class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = ["id", "name", "level", "stage"]
