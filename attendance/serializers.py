from rest_framework import serializers
from .models import AttendanceRecord


class AttendanceRecordSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, help_text="Unique attendance record ID.")
    course = serializers.PrimaryKeyRelatedField(read_only=True, help_text="Course ID.")
    student = serializers.PrimaryKeyRelatedField(read_only=True, help_text="Student user ID.")
    date = serializers.DateField(help_text="Attendance date (YYYY-MM-DD).")
    status = serializers.ChoiceField(
        choices=AttendanceRecord.Status.choices,
        help_text="Attendance status: `present`, `absent`, or `late`.",
    )
    marked_by = serializers.PrimaryKeyRelatedField(
        read_only=True, help_text="Teacher who marked the attendance."
    )

    class Meta:
        model = AttendanceRecord
        fields = ["id", "course", "student", "date", "status", "marked_by"]
        read_only_fields = ["id", "marked_by"]


class AttendanceRecordInputSerializer(serializers.Serializer):
    student_id = serializers.IntegerField(
        help_text="ID of the student."
    )
    status = serializers.ChoiceField(
        choices=AttendanceRecord.Status.choices,
        help_text="Attendance status for this student.",
    )


class MarkAttendanceSerializer(serializers.Serializer):
    course = serializers.IntegerField(
        help_text="ID of the course for which attendance is being marked."
    )
    date = serializers.DateField(
        help_text="Date of the class session (YYYY-MM-DD)."
    )
    records = AttendanceRecordInputSerializer(
        many=True,
        help_text="List of per-student attendance entries. One entry per enrolled student.",
    )
