from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import Course, Enrollment, Lesson


class LessonSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, help_text="Unique lesson ID.")
    title = serializers.CharField(
        max_length=255,
        help_text="Lesson title.",
    )
    content = serializers.CharField(
        help_text="Full lesson body (supports plain text or Markdown).",
    )
    order = serializers.IntegerField(
        default=0,
        help_text="Display order within the course. Lower numbers appear first.",
    )
    created_at = serializers.DateTimeField(
        read_only=True, help_text="Lesson creation timestamp."
    )

    class Meta:
        model = Lesson
        fields = ["id", "title", "content", "order", "created_at"]
        read_only_fields = ["id", "created_at"]


class CourseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, help_text="Unique course ID.")
    title = serializers.CharField(help_text="Course title.")
    description = serializers.CharField(
        help_text="Course overview shown to students.",
        required=False,
    )
    teacher = UserSerializer(read_only=True, help_text="Teacher who owns the course.")
    created_at = serializers.DateTimeField(
        read_only=True, help_text="Course creation timestamp."
    )

    class Meta:
        model = Course
        fields = ["id", "title", "description", "teacher", "created_at"]
        read_only_fields = ["id", "teacher", "created_at"]


class CourseWriteSerializer(serializers.ModelSerializer):
    title = serializers.CharField(
        max_length=255,
        help_text="Course title (required).",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional course description.",
    )

    class Meta:
        model = Course
        fields = ["title", "description"]


class EnrollmentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, help_text="Enrollment record ID.")
    student = UserSerializer(read_only=True, help_text="The enrolled student.")
    enrolled_at = serializers.DateTimeField(
        read_only=True, help_text="Enrollment timestamp."
    )

    class Meta:
        model = Enrollment
        fields = ["id", "student", "enrolled_at"]
        read_only_fields = ["id", "student", "enrolled_at"]


class AttendanceResultSerializer(serializers.Serializer):
    status = serializers.CharField(
        help_text="Attendance status: present, late, or absent."
    )
    date = serializers.DateField(help_text="Date of the attendance.")
    is_new = serializers.BooleanField(
        help_text="True if this is a new attendance record."
    )


class StudentAttendanceSerializer(serializers.Serializer):
    student_id = serializers.IntegerField(help_text="Student user ID.")
    student_name = serializers.CharField(
        help_text="Full name or username of the student."
    )
    status = serializers.CharField(
        allow_null=True, help_text="Attendance status or null if not marked."
    )


class LessonAttendanceSummarySerializer(serializers.Serializer):
    lesson_id = serializers.IntegerField(help_text="Lesson ID.")
    lesson_title = serializers.CharField(help_text="Lesson title.")
    total_enrolled = serializers.IntegerField(
        help_text="Total number of enrolled students."
    )
    attendance = StudentAttendanceSerializer(
        many=True, help_text="List of student attendance records."
    )
