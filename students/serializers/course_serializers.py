from rest_framework import serializers


class CourseListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    completion_percentage = serializers.FloatField()
    status = serializers.CharField()


class LessonSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    is_completed = serializers.BooleanField()


class SyllabusSerializer(serializers.Serializer):
    lesson_id = serializers.IntegerField()
    title = serializers.CharField()
    is_completed = serializers.BooleanField()


class QuizBriefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()


class AssignmentBriefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    deadline = serializers.DateTimeField()


class CourseDetailSerializer(serializers.Serializer):
    course_name = serializers.CharField()
    completion_percentage = serializers.FloatField()
    lessons = LessonSerializer(many=True)
    quizzes = QuizBriefSerializer(many=True)
    assignments = AssignmentBriefSerializer(many=True)
