from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import Course, CourseProgress, Lesson, LessonActivity, Quiz, QuizAttempt, StudentCourse


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
    xp_reward = serializers.IntegerField(read_only=True, help_text="XP reward for completing this lesson.")
    bonus_xp = serializers.IntegerField(read_only=True, help_text="Bonus XP for completing this lesson.")
    status = serializers.CharField(read_only=True, help_text="Lesson status: draft or published.")
    created_at = serializers.DateTimeField(
        read_only=True, help_text="Lesson creation timestamp."
    )

    class Meta:
        model = Lesson
        fields = ["id", "title", "content", "order", "xp_reward", "bonus_xp", "status", "created_at"]
        read_only_fields = ["id", "xp_reward", "bonus_xp", "status", "created_at"]


class CourseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, help_text="Unique course ID.")
    title = serializers.CharField(help_text="Course title.")
    description = serializers.CharField(
        help_text="Course overview shown to students.",
        required=False,
    )
    teacher = UserSerializer(read_only=True, help_text="Teacher who owns the course.")
    is_published = serializers.BooleanField(read_only=True, help_text="Whether the course is published.")
    created_at = serializers.DateTimeField(
        read_only=True, help_text="Course creation timestamp."
    )

    class Meta:
        model = Course
        fields = ["id", "title", "description", "teacher", "is_published", "created_at"]
        read_only_fields = ["id", "teacher", "is_published", "created_at"]


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


class StudentCourseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    student = UserSerializer(read_only=True)
    enrolled_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = StudentCourse
        fields = ["id", "student", "is_active", "enrolled_at"]
        read_only_fields = ["id", "student", "is_active", "enrolled_at"]


class CourseProgressSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    study_time_formatted = serializers.SerializerMethodField()

    class Meta:
        model = CourseProgress
        fields = [
            "student_id",
            "student_name",
            "progress_percentage",
            "study_time_seconds",
            "study_time_formatted",
            "last_activity",
            "completion_status",
        ]

    def get_student_name(self, obj: CourseProgress) -> str:
        return obj.student.get_full_name() or obj.student.username

    def get_study_time_formatted(self, obj: CourseProgress) -> str:
        hours = obj.study_time_seconds // 3600
        minutes = (obj.study_time_seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = [
            "id", "course_id", "lesson_id", "teacher", "title", "max_score",
            "duration_minutes", "xp_reward", "start_time", "end_time", "is_locked",
            "created_at",
        ]
        read_only_fields = ["id", "teacher", "is_locked", "created_at"]


class QuizAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = ["id", "attempt_number", "score", "submitted_at"]
        read_only_fields = ["id", "attempt_number", "submitted_at"]


class QuizSubmitSerializer(serializers.Serializer):
    score = serializers.DecimalField(
        max_digits=5, decimal_places=2, help_text="Score for this attempt."
    )


class LessonActivitySerializer(serializers.ModelSerializer):
    lesson_title = serializers.SerializerMethodField()

    class Meta:
        model = LessonActivity
        fields = [
            "id",
            "lesson_id",
            "lesson_title",
            "watch_duration_seconds",
            "completed",
            "last_opened_at",
        ]
        read_only_fields = ["id", "watch_duration_seconds", "completed", "last_opened_at"]

    def get_lesson_title(self, obj: LessonActivity) -> str:
        return obj.lesson.title


class LessonTrackSerializer(serializers.Serializer):
    watch_duration_seconds = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
        help_text="Incremental watch time in seconds for this session.",
    )
    completed = serializers.BooleanField(
        required=False, default=False, help_text="Mark lesson as completed."
    )


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
