from rest_framework import serializers
from .models import Student, Grade
from schools.models import School

class AddStudentSerializer(serializers.ModelSerializer):
    grade = serializers.PrimaryKeyRelatedField(queryset=Grade.objects.all(), required=True)
    school_code = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = Student
        fields = ['full_name', 'grade', 'school_code']

    def create(self, validated_data):
        school_code = validated_data.pop('school_code')
        school = School.objects.get(school_code=school_code)

        student = Student.objects.create(
            parent=self.context['request'].user,
            school=school,
            **validated_data
        )
        return student