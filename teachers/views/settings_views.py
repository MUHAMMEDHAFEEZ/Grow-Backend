from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.permissions import IsTeacher
from teachers.selectors import get_teacher_profile
from teachers.serializers import (
    NotificationPreferenceSerializer,
    TeacherProfileSerializer,
    TeacherProfileUpdateSerializer,
)
from teachers.services import update_notification_preferences, update_teacher_profile


@extend_schema(
    tags=["Teacher Settings"],
    summary="Get teacher profile",
    responses={200: TeacherProfileSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def get_profile(request: Request) -> Response:
    profile = get_teacher_profile(request.user)
    if not profile:
        return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(TeacherProfileSerializer(profile).data)


@extend_schema(
    tags=["Teacher Settings"],
    summary="Update teacher profile",
    request=TeacherProfileUpdateSerializer,
    responses={200: TeacherProfileSerializer},
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsTeacher])
def update_profile(request: Request) -> Response:
    serializer = TeacherProfileUpdateSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    profile = update_teacher_profile(user=request.user, **serializer.validated_data)
    return Response(TeacherProfileSerializer(profile).data)


@extend_schema(
    tags=["Teacher Settings"],
    summary="Get notification preferences",
    responses={200: NotificationPreferenceSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def get_notification_prefs(request: Request) -> Response:
    profile = get_teacher_profile(request.user)
    if not profile:
        return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(NotificationPreferenceSerializer(profile.user.notification_preferences).data)


@extend_schema(
    tags=["Teacher Settings"],
    summary="Update notification preferences",
    request=NotificationPreferenceSerializer,
    responses={200: NotificationPreferenceSerializer},
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsTeacher])
def update_notification_prefs(request: Request) -> Response:
    serializer = NotificationPreferenceSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    prefs = update_notification_preferences(user=request.user, **serializer.validated_data)
    return Response(NotificationPreferenceSerializer(prefs).data)
