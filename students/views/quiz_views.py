from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from courses.models import Quiz, QuizAttempt
from core.permissions import IsStudent
from students.serializers.quiz_serializers import (
    QuizResultSerializer,
    QuizStartSerializer,
    QuizSubmitSerializer,
    StudentOptionSerializer,
)
from students.services.xp_service import award_xp


@extend_schema(
    tags=["Student Quizzes"],
    summary="Start quiz",
    description="Get quiz questions and start attempt.",
    request=None,
    responses={200: QuizStartSerializer},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def start_quiz_view(request, quiz_id):
    try:
        quiz = Quiz.objects.prefetch_related("questions__options").get(id=quiz_id)
    except Quiz.DoesNotExist:
        return Response({"error": "Quiz not found"}, status=404)

    questions_qs = quiz.questions.all().order_by("order")
    questions = []
    question_map = []
    for idx, q in enumerate(questions_qs, start=1):
        options = StudentOptionSerializer(q.options.all(), many=True).data
        questions.append({
            "id": q.id,
            "text": q.text,
            "order": q.order,
            "options": options,
        })
        question_map.append({"question_number": idx, "status": "unanswered"})

    data = {
        "quiz_id": quiz.id,
        "title": quiz.title,
        "time_limit_seconds": quiz.duration_minutes * 60 if quiz.duration_minutes else None,
        "questions": questions,
        "question_map": question_map,
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

    questions = quiz.questions.prefetch_related("options").all()
    correct_map = {}
    for q in questions:
        correct_map[q.id] = [
            o.text for o in q.options.all() if o.is_correct
        ]

    answers = serializer.validated_data["answers"]
    correct_count = 0
    for ans in answers:
        correct_texts = correct_map.get(ans["question_id"], [])
        if ans["answer"] in correct_texts:
            correct_count += 1

    total = len(questions)
    max_score = float(quiz.max_score)
    score = round((correct_count / total) * max_score, 2) if total > 0 else 0
    percentage = (score / max_score * 100) if max_score > 0 else 0

    QuizAttempt.objects.create(
        student=request.user,
        quiz=quiz,
        score=score,
        attempt_number=attempt_number,
    )

    xp_amount = 0
    if percentage >= 50:
        xp_amount = quiz.xp_reward or 0
        award_xp(request.user, "quiz", quiz_id, xp_amount)

    result = {
        "score": score,
        "percentage": percentage,
        "passed": percentage >= 50,
        "xp_awarded": xp_amount,
    }
    result_serializer = QuizResultSerializer(result)
    return Response(result_serializer.data)
