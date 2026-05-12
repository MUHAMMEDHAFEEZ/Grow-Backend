from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from courses.models import Quiz, QuizAttempt
from students.permissions import IsStudent
from students.serializers.quiz_serializers import (
    QuizResultSerializer,
    QuizStartSerializer,
    QuizSubmitSerializer,
)
from students.services.xp_service import award_xp


@extend_schema(
    tags=["Student Quizzes"],
    summary="Start quiz",
    description="Get quiz questions and start attempt.",
    responses={200: QuizStartSerializer},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def start_quiz_view(request, quiz_id):
    try:
        quiz = Quiz.objects.get(id=quiz_id)
    except Quiz.DoesNotExist:
        return Response({"error": "Quiz not found"}, status=404)

    existing_attempt = QuizAttempt.objects.filter(
        student=request.user, quiz=quiz
    ).first()

    data = {
        "quiz_id": quiz.id,
        "title": quiz.title,
        "time_limit_seconds": None,
        "questions": [],
        "question_map": [],
    }
    serializer = QuizStartSerializer(data)
    return Response(serializer.data)


@extend_schema(
    tags=["Student Quizzes"],
    summary="Submit quiz",
    description="Submit quiz answers and get score.",
    request=QuizSubmitSerializer,
    responses={200: QuizResultSerializer},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def submit_quiz_view(request, quiz_id):
    try:
        quiz = Quiz.objects.get(id=quiz_id)
    except Quiz.DoesNotExist:
        return Response({"error": "Quiz not found"}, status=404)

    serializer = QuizSubmitSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    last_attempt = (
        QuizAttempt.objects.filter(student=request.user, quiz=quiz)
        .order_by("-attempt_number")
        .first()
    )
    attempt_number = (last_attempt.attempt_number + 1) if last_attempt else 1

    answers = serializer.validated_data["answers"]
    score = 0
    max_score = float(quiz.max_score)
    percentage = (score / max_score * 100) if max_score > 0 else 0

    QuizAttempt.objects.create(
        student=request.user,
        quiz=quiz,
        score=score,
        attempt_number=attempt_number,
    )

    xp_amount = 0
    if percentage >= 50:
        xp_amount = 200
        award_xp(request.user, "quiz", quiz_id, xp_amount)

    result = {
        "score": score,
        "percentage": percentage,
        "passed": percentage >= 50,
        "xp_awarded": xp_amount,
    }
    result_serializer = QuizResultSerializer(result)
    return Response(result_serializer.data)
