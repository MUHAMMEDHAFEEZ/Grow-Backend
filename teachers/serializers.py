from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from assignments.models import Assignment
from courses.models import Course, Lesson, Quiz, Question, AnswerOption
from submissions.models import Submission

from .models import AuditLog, TeacherProfile, TeacherNotification, TeacherNotificationPreference


class TeacherSignupSerializer(serializers.Serializer):
    school_id = serializers.IntegerField()
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    teacher_code = serializers.CharField(max_length=50)


class TeacherLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user_id = serializers.IntegerField()
    role = serializers.CharField()


class SendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)


@extend_schema_serializer(component_name="TeacherResetPasswordRequest")
class ResetPasswordSerializer(serializers.Serializer):
    reset_token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class TeacherProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    school_name = serializers.SerializerMethodField()
    teacher_id = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        fields = [
            "full_name", "email", "school_name", "teacher_id",
            "bio", "avatar", "preferred_language",
        ]
        read_only_fields = ["full_name", "email", "school_name", "teacher_id"]

    def get_full_name(self, obj: TeacherProfile) -> str:
        return obj.user.get_full_name() or obj.user.username

    def get_email(self, obj: TeacherProfile) -> str:
        return obj.user.email

    def get_school_name(self, obj: TeacherProfile) -> str:
        return obj.school.name if obj.school else ""

    def get_teacher_id(self, obj: TeacherProfile) -> int:
        return obj.user.id


class TeacherProfileUpdateSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(max_length=255, required=False)
    preferred_language = serializers.CharField(max_length=10, required=False)

    class Meta:
        model = TeacherProfile
        fields = ["bio", "avatar", "preferred_language", "full_name"]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherNotificationPreference
        fields = ["email_notifications", "missing_assignments", "new_submissions"]


class TeacherCourseListSerializer(serializers.ModelSerializer):
    lesson_count = serializers.SerializerMethodField()
    enrolled_students = serializers.SerializerMethodField()
    total_xp = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id", "title", "description", "grade", "is_published",
            "lesson_count", "enrolled_students", "total_xp",
            "created_at",
        ]

    def get_lesson_count(self, obj: Course) -> int:
        return getattr(obj, "_lesson_count", 0)

    def get_enrolled_students(self, obj: Course) -> int:
        return getattr(obj, "_enrolled_count", 0)

    def get_total_xp(self, obj: Course) -> int:
        return getattr(obj, "_total_xp", 0)


class TeacherCourseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["title", "description", "grade", "is_published"]


class TeacherLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = [
            "id", "title", "content", "order", "status",
            "video_url", "video_file", "pdf_file", "resources",
            "xp_reward", "bonus_xp",
            "start_time", "end_time", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class LessonReorderSerializer(serializers.Serializer):
    ordered_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )

    def validate_ordered_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("ordered_ids must not contain duplicates.")
        return value


class TeacherAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = [
            "id", "course", "title", "description", "due_date",
            "xp_reward", "late_penalty_xp", "teacher_file", "max_score",
            "created_at",
        ]
        read_only_fields = ["id", "course", "created_at"]


class TeacherAssignmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = [
            "title", "description", "due_date",
            "xp_reward", "late_penalty_xp", "teacher_file", "max_score",
        ]


class TeacherSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id", "student", "student_name", "content", "file",
            "status", "raw_score", "normalized_score",
            "xp_awarded", "feedback", "is_graded", "submitted_at",
        ]

    def get_student_name(self, obj: Submission) -> str:
        return obj.student.get_full_name() or obj.student.username


class GradeSubmissionSerializer(serializers.Serializer):
    raw_score = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0)
    feedback = serializers.CharField(required=False, allow_blank=True)


class TeacherQuizSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            "id", "course", "lesson", "title", "max_score",
            "duration_minutes", "xp_reward",
            "start_time", "end_time", "is_locked",
            "questions", "created_at",
        ]
        read_only_fields = ["id", "is_locked", "created_at"]

    def get_questions(self, obj: Quiz) -> list:
        return QuestionSerializer(obj.questions.all(), many=True).data


class QuestionSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ["id", "text", "order", "options"]

    def get_options(self, obj: Question) -> list:
        return AnswerOptionSerializer(obj.options.all(), many=True).data


class AnswerOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerOption
        fields = ["id", "text", "is_correct"]


class QuestionWriteSerializer(serializers.Serializer):
    text = serializers.CharField()
    order = serializers.IntegerField(default=0)
    options = serializers.ListField(
        child=serializers.DictField(),
        min_length=4,
    )


class QuizWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    course_id = serializers.IntegerField()
    lesson_id = serializers.IntegerField(required=False, allow_null=True)
    max_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    duration_minutes = serializers.IntegerField(min_value=1)
    xp_reward = serializers.IntegerField(min_value=0)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    questions = QuestionWriteSerializer(many=True, min_length=1)


class QuizResultSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    raw_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    max_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    normalized_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    xp_earned = serializers.IntegerField()
    status = serializers.CharField()


class QuizFeedbackSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    message = serializers.CharField()


class TeacherDashboardSerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    total_courses = serializers.IntegerField()
    assignments_created = serializers.IntegerField()
    active_quizzes = serializers.IntegerField()
    top_performance = serializers.ListField()
    need_review = serializers.ListField()
    recent_student_activity = serializers.ListField()


class TeacherStudentSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    avg_score_pct = serializers.FloatField()
    attendance_rate = serializers.FloatField()
    total_xp = serializers.IntegerField()
    status = serializers.CharField()


class TeacherStudentListSerializer(serializers.Serializer):
    avg_performance = serializers.FloatField()
    avg_attendance = serializers.FloatField()
    total_students = serializers.IntegerField()
    need_attention = serializers.IntegerField()
    students = TeacherStudentSerializer(many=True)


class TeacherNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherNotification
        fields = ["id", "event_type", "reference_type", "reference_id", "message", "is_read", "created_at"]
        read_only_fields = ["id", "created_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ["id", "actor_type", "actor_id", "action", "resource_type", "resource_id", "metadata", "ip_address", "created_at"]
