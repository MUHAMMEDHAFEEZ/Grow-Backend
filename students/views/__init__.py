from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from accounts.serializers import SchoolSerializer

from students.serializers import DashboardResponseSerializer
from students.models import Student, Grade
from schools.models import School
from students import services


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
@extend_schema(
    tags=["Schools"],
    summary="List all schools",
    description="Returns a list of all schools with their names, codes, and types.",
    responses={200: SchoolSerializer(many=True)},
    operation_id="schools_list",
)
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