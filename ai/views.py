import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from ai.serializers import ChatRequestSerializer, ChatResponseSerializer
from ai import services

logger = logging.getLogger(__name__)


class AiUserThrottle(UserRateThrottle):
    scope = "ai"


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
@throttle_classes([AiUserThrottle])
def chat(request):
    """Chat with AI assistant using student context."""
    student_profile = getattr(request.user, 'student_profile', None)
    if student_profile is None:
        return Response(
            {"error": "Student profile not found"},
            status=404
        )

    serializer = ChatRequestSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    message = serializer.validated_data['message']
    logger.info("AI chat request — student=%s message_len=%d", request.user.id, len(message))

    result = services.chat_with_student_context(request.user, message)

    logger.info("AI chat response — student=%s reply_len=%d", request.user.id, len(result['reply']))

    response_serializer = ChatResponseSerializer(result)
    return Response(response_serializer.data)
