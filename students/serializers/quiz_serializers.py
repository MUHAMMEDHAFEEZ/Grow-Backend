from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers


class QuestionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    text = serializers.CharField()
    options = serializers.ListField(child=serializers.CharField(), allow_null=True)


class QuestionMapSerializer(serializers.Serializer):
    question_number = serializers.IntegerField()
    status = serializers.CharField()


class QuizStartSerializer(serializers.Serializer):
    quiz_id = serializers.IntegerField()
    title = serializers.CharField()
    time_limit_seconds = serializers.IntegerField(allow_null=True)
    questions = QuestionSerializer(many=True)
    question_map = QuestionMapSerializer(many=True)


class AnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answer = serializers.CharField()


@extend_schema_serializer(component_name="StudentQuizSubmitRequest")
class QuizSubmitSerializer(serializers.Serializer):
    answers = AnswerSerializer(many=True)


@extend_schema_serializer(component_name="StudentQuizResult")
class QuizResultSerializer(serializers.Serializer):
    score = serializers.DecimalField(max_digits=5, decimal_places=2)
    percentage = serializers.FloatField()
    passed = serializers.BooleanField()
    xp_awarded = serializers.IntegerField()
