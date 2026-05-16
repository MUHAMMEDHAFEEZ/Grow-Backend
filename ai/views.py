from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ai.serializers import ChatRequestSerializer, ChatResponseSerializer
from ai import services


@extend_schema(
    tags=["AI"],
    summary="Chat with AI assistant",
    description="Send a message to the AI assistant with student context for personalized help.",
    request=ChatRequestSerializer,
    responses={
        200: OpenApiResponse(response=ChatResponseSerializer, description="AI response."),
        400: OpenApiResponse(description="Invalid request."),
        404: OpenApiResponse(description="Student profile not found."),
    },
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat(request):
    """Chat with AI assistant using student context."""
    if not hasattr(request.user, 'student_profile'):
        return Response(
            {"error": "Student profile not found"},
            status=404
        )

    serializer = ChatRequestSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    student = request.user.student_profile
    message = serializer.validated_data['message']

    result = services.chat_with_student_context(student, message)

    response_serializer = ChatResponseSerializer(result)
    return Response(response_serializer.data)