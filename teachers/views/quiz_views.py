from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.permissions import IsTeacher
from teachers.serializers import (
    QuizFeedbackSerializer,
    QuizResultSerializer,
    QuizWriteSerializer,
    TeacherQuizSerializer,
)
from teachers.selectors import get_quiz_detail, get_quiz_results, get_teacher_quizzes
from teachers.services import create_teacher_quiz, send_quiz_feedback, update_teacher_quiz


@extend_schema(
    tags=["Teacher Quizzes"],
    summary="List quizzes",
    responses={200: TeacherQuizSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def list_quizzes(request: Request) -> Response:
    course_id = request.query_params.get("course_id")
    quizzes = get_teacher_quizzes(request.user, course_id)
    return Response(TeacherQuizSerializer(quizzes, many=True).data)


@extend_schema(
    tags=["Teacher Quizzes"],
    summary="Create quiz",
    request=QuizWriteSerializer,
    responses={201: TeacherQuizSerializer},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTeacher])
def create_quiz(request: Request) -> Response:
    serializer = QuizWriteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    quiz = create_teacher_quiz(teacher=request.user, **serializer.validated_data)
    return Response(TeacherQuizSerializer(quiz).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Teacher Quizzes"],
    summary="Get quiz detail",
    responses={200: TeacherQuizSerializer, 404: OpenApiResponse(description="Not found.")},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def get_quiz(request: Request, quiz_id: int) -> Response:
    quiz = get_quiz_detail(quiz_id)
    if not quiz or quiz.teacher_id != request.user.id:
        return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(TeacherQuizSerializer(quiz).data)


@extend_schema(
    tags=["Teacher Quizzes"],
    summary="Update quiz",
    request=QuizWriteSerializer,
    responses={200: TeacherQuizSerializer},
)
@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated, IsTeacher])
def update_quiz(request: Request, quiz_id: int) -> Response:
    serializer = QuizWriteSerializer(data=request.data, partial=request.method == "PATCH")
    serializer.is_valid(raise_exception=True)
    quiz = update_teacher_quiz(teacher=request.user, quiz_id=quiz_id, **serializer.validated_data)
    return Response(TeacherQuizSerializer(quiz).data)


@extend_schema(
    tags=["Teacher Quizzes"],
    summary="Quiz results",
    responses={200: QuizResultSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def quiz_results(request: Request, quiz_id: int) -> Response:
    quiz = get_quiz_detail(quiz_id)
    if not quiz or quiz.teacher_id != request.user.id:
        return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    results = get_quiz_results(quiz)
    completed = sum(1 for r in results if r["status"] == "completed")
    enrolled = get_teacher_quizzes(request.user).count()
    return Response({
        "avg_score_pct": round(sum(r["normalized_score"] for r in results) / len(results), 2) if results else 0,
        "completion_rate": round((completed / enrolled) * 100, 2) if enrolled > 0 else 0,
        "results": results,
    })


@extend_schema(
    tags=["Teacher Quizzes"],
    summary="Send feedback to student",
    request=QuizFeedbackSerializer,
    responses={200: OpenApiResponse(description="Feedback sent.")},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTeacher])
def send_feedback(request: Request, quiz_id: int) -> Response:
    serializer = QuizFeedbackSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    send_quiz_feedback(
        teacher=request.user,
        quiz_id=quiz_id,
        student_id=serializer.validated_data["student_id"],
        message=serializer.validated_data["message"],
    )
    return Response({"detail": "Feedback sent."})
