from rest_framework import serializers


class ParentGPASerializer(serializers.Serializer):
    value = serializers.FloatField()
    change = serializers.FloatField()


class StudyHoursSerializer(serializers.Serializer):
    total = serializers.FloatField()
    weekly = serializers.FloatField()
    progress = serializers.IntegerField()


class SubjectPerformanceSerializer(serializers.Serializer):
    name = serializers.CharField()
    average = serializers.FloatField()
    grade = serializers.CharField()


class UpcomingItemSerializer(serializers.Serializer):
    type = serializers.CharField()
    id = serializers.IntegerField()
    title = serializers.CharField()
    date = serializers.CharField()
    course = serializers.CharField()


class RecentActivitySerializer(serializers.Serializer):
    type = serializers.CharField()
    title = serializers.CharField()
    timestamp = serializers.CharField()


class DashboardSerializer(serializers.Serializer):
    gpa = ParentGPASerializer()
    study_hours = StudyHoursSerializer()
    xp = serializers.DictField()
    engagement = serializers.IntegerField()
    subject_performance = SubjectPerformanceSerializer(many=True)
    upcoming_schedule = UpcomingItemSerializer(many=True)
    recent_activity = RecentActivitySerializer(many=True)


class StudentListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    student_id = serializers.CharField()
    grade_name = serializers.CharField(source="grade.name", allow_null=True)
    school_name = serializers.CharField(source="school.name", allow_null=True)


class TrendPointSerializer(serializers.Serializer):
    period = serializers.CharField()
    average = serializers.FloatField()


class StudyHoursPointSerializer(serializers.Serializer):
    period = serializers.CharField()
    hours = serializers.FloatField()


class SubjectBreakdownSerializer(serializers.Serializer):
    name = serializers.CharField()
    average = serializers.FloatField()
    grade = serializers.CharField()


class AnalyticsSerializer(serializers.Serializer):
    overall_academic_trend = TrendPointSerializer(many=True)
    study_hours = StudyHoursPointSerializer(many=True)
    subject_breakdown = SubjectBreakdownSerializer(many=True)


class CalendarDaySerializer(serializers.Serializer):
    date = serializers.CharField()
    status = serializers.CharField()


class AttendanceSerializer(serializers.Serializer):
    total_study_hours = serializers.FloatField()
    study_streak = serializers.IntegerField()
    attendance_rate = serializers.FloatField()
    activity_calendar = CalendarDaySerializer(many=True)


class AssignmentSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    submitted = serializers.IntegerField()
    missing = serializers.IntegerField()


class SubjectReportSerializer(serializers.Serializer):
    name = serializers.CharField()
    average = serializers.FloatField()
    completed = serializers.IntegerField()


class ReportSerializer(serializers.Serializer):
    month = serializers.CharField()
    overall_average = serializers.FloatField()
    assignment_summary = AssignmentSummarySerializer()
    total_xp = serializers.IntegerField()
    subject_performance = SubjectReportSerializer(many=True)


class ParentNotificationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    body = serializers.CharField()
    event_type = serializers.CharField()
    is_read = serializers.BooleanField()
    reference_id = serializers.IntegerField(allow_null=True)
    created_at = serializers.DateTimeField()


class LinkedStudentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    student_id = serializers.CharField()
    grade_name = serializers.CharField(source="grade.name", allow_null=True)
    school_name = serializers.CharField(source="school.name", allow_null=True)


class SettingsSerializer(serializers.Serializer):
    full_name = serializers.CharField(source="user.username")
    email = serializers.EmailField(source="user.email", read_only=True)
    notifications_enabled = serializers.BooleanField(source="user.notifications_enabled")
    linked_students = LinkedStudentSerializer(many=True, read_only=True)

    class Meta:
        fields = ["full_name", "email", "notifications_enabled", "linked_students"]