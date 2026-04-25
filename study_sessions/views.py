from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from study_sessions.models import StudySession
from study_sessions import services
from study_sessions import selectors
from study_sessions.serializers import (
    StudySessionSerializer,
    SessionTotalSerializer,
)


class SessionStartView(APIView):
    """
    POST /sessions/start/
    Start a new study session.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        try:
            session = services.start_session(user)
            serializer = StudySessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except services.ActiveSessionExistsError as e:
            return Response(
                {"error": str(e), "code": "active_session_exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class SessionEndView(APIView):
    """
    POST /sessions/end/
    End the current study session.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        try:
            session = services.end_session(user)

            if session.xp_earned > 0:
                from xp.services import award_study_session_xp

                award_study_session_xp(session)

            serializer = StudySessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except services.NoActiveSessionError as e:
            return Response(
                {"error": str(e), "code": "no_active_session"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class SessionActiveView(APIView):
    """
    GET /sessions/active/
    Get the currently active session.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        session = selectors.get_active_session(request.user)

        if not session:
            return Response(
                {"error": "No active session"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = StudySessionSerializer(session)
        return Response(serializer.data)


class SessionTotalView(APIView):
    """
    GET /sessions/total/
    Get total study time.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        totals = selectors.get_total_study_time(request.user)
        serializer = SessionTotalSerializer(totals)
        return Response(serializer.data)


class SessionListView(APIView):
    """
    GET /sessions/
    List all sessions for the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))

        sessions = selectors.get_study_sessions(
            request.user, page=page, page_size=page_size
        )

        serializer = StudySessionSerializer(sessions, many=True)
        return Response(
            {
                "results": serializer.data,
                "count": selectors.get_session_count(request.user),
            }
        )
