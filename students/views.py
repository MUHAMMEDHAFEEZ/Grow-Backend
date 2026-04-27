from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from .serializers import AddStudentSerializer, DashboardResponseSerializer
from .models import Student
from schools.models import School
from .models import Grade
from . import services
from . import selectors



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_student(request):
    if request.user.role != 'parent':
        return Response({"error": "Only parents can add students"}, status=403)

    serializer = AddStudentSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        full_name = serializer.validated_data['full_name']
        grade = serializer.validated_data['grade']
        school_code = serializer.validated_data.get('school_code')

        # البحث عن الطالب الموجود أولاً
        existing_student = Student.objects.filter(
            full_name__iexact=full_name,
            grade=grade,
            school__school_code=school_code
        ).first()

        if existing_student:
            # ربط الطالب بالـ Parent إذا لم يكن مربوط
            if existing_student.parent != request.user:
                existing_student.parent = request.user
                existing_student.save()
            
            return Response({
                "message": "Student already exists and has been linked to your account",
                "student_id": existing_student.student_id,
                "full_name": existing_student.full_name,
                "linked": True
            }, status=200)

        # لو مش موجود → ننشئ طالب جديد
        student = serializer.save()
        return Response({
            "message": "New student created and linked successfully",
            "student_id": student.student_id,
            "generated_password": student.generated_password,
            "full_name": student.full_name,
            "linked": True
        }, status=201)

    return Response(serializer.errors, status=400)


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