from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.exceptions import Conflict, NotFound, RateLimitExceeded, ValidationError

from .serializers import AddStudentSerializer, DashboardResponseSerializer
from .models import Student, Grade
from schools.models import School
from . import services
from . import selectors


@extend_schema(
    tags=["Parent"],
    summary="Add student with verification code",
    description=(
        "Links an existing student to the authenticated parent using "
        "the student's ID and parent_access_code."
    ),
    request=AddStudentSerializer,
    responses={
        200: {"description": "Student linked successfully."},
        400: {"description": "Invalid access code or bad request."},
        404: {"description": "Student not found."},
        409: {"description": "Student already linked to another parent."},
        429: {"description": "Too many failed attempts. Rate limited."},
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_student(request):
    if request.user.role != "parent":
        return Response({"error": "Only parents can add students"}, status=403)

    serializer = AddStudentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    try:
        student = services.link_student_to_parent(
            parent=request.user,
            student_id=serializer.validated_data["student_id"],
            parent_access_code=serializer.validated_data["parent_access_code"],
        )
    except RateLimitExceeded as exc:
        return Response({"error": exc.detail}, status=429)
    except NotFound as exc:
        return Response({"error": exc.detail}, status=404)
    except Conflict as exc:
        return Response({"error": exc.detail}, status=409)
    except ValidationError as exc:
        return Response({"error": exc.detail}, status=400)

    return Response({
        "message": "Student linked successfully",
        "student_id": student.student_id,
        "full_name": student.full_name,
    }, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_has_students(request):
    if request.user.role != 'parent':
        return Response({"has_students": False}, status=403)
    
    has_students = Student.objects.filter(parent=request.user).exists()
    
    return Response({
        "has_students": has_students
    })


# APIs جديدة للـ React (هتحتاجها في Add Student)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_schools(request):
    """ترجع قائمة المدارس"""
    schools = School.objects.all().values('id', 'name', 'school_code', 'school_type')
    return Response(list(schools))


@api_view(['GET'])
@permission_classes([AllowAny])
def get_grades(request):
    """ترجع قائمة الدرجات"""
    grades = Grade.objects.all().values('id', 'name', 'level', 'stage')
    return Response(list(grades))

@api_view(['GET'])
@permission_classes([AllowAny])
def get_students(request):
    """ترجع قايمة الطلاب الي في المدارس"""
    students = Student.objects.all().values('id', 'full_name', 'student_id', 'grade__name', 'school__name')
    return Response(list(students))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """Get student dashboard."""
    if not hasattr(request.user, 'student_profile'):
        return Response(
            {"error": "Student profile not found"},
            status=404
        )

    student = request.user.student_profile

    dashboard_data = services.get_student_dashboard(student)

    serializer = DashboardResponseSerializer(dashboard_data)
    return Response(serializer.data)