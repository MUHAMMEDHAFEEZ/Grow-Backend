from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from schools.models import School, Grade, Class as SchoolClass

User = get_user_model()

class Student(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='student_profile', 
        null=True, 
        blank=True
    )
    
    parent = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='children', 
        null=True, 
        blank=True
    )
    
    school = models.ForeignKey(
        School, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    grade = models.ForeignKey(
        Grade, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    class_fk = models.ForeignKey(
        SchoolClass,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="students",
        help_text="The auto-generated class this student belongs to.",
    )

    full_name = models.CharField(max_length=150)
    school_code = models.CharField(max_length=50, blank=True, null=True)

    parent_access_code = models.CharField(max_length=20, blank=True, null=True)
    student_id = models.CharField(max_length=30, unique=True, editable=False)
    generated_password = models.CharField(max_length=30, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.student_id:
            if self.grade:
                grade_code = f"G{self.grade.level}"
            else:
                grade_code = "GX"
            
            import random
            
            while True:
                random_part = random.randint(100, 999)
                candidate_id = f"STU-2024-{grade_code}-{random_part}"
                
                if not Student.objects.filter(student_id=candidate_id).exists():
                    self.student_id = candidate_id
                    self.generated_password = candidate_id
                    break

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"


class StudentAddRateLimit(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_add_rate_limit"
    )
    failed_attempts = models.IntegerField(default=0)
    window_start = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"StudentAddRateLimit(user={self.user_id}, attempts={self.failed_attempts})"


class LoginHistory(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_login_history",
        limit_choices_to={"role": "student"},
    )
    login_date = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "login_date"], name="unique_daily_login"),
        ]
        indexes = [
            models.Index(fields=["student", "login_date"]),
        ]

    def __str__(self):
        return f"LoginHistory(student={self.student_id}, date={self.login_date})"


class StudentSession(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_sessions",
        limit_choices_to={"role": "student"},
    )
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True, help_text="Duration in seconds")
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "is_active"]),
        ]

    def __str__(self):
        return f"StudentSession(student={self.student_id}, active={self.is_active})"


class StudentCourseProgress(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_course_progress",
        limit_choices_to={"role": "student"},
    )
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, related_name="student_progress"
    )
    completed_lessons = models.IntegerField(default=0)
    total_lessons = models.IntegerField(default=0)
    completion_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "course"], name="unique_student_course_progress"),
        ]

    def __str__(self):
        return f"StudentCourseProgress(student={self.student_id}, course={self.course_id}, {self.completion_percentage}%)"


class LessonCompletion(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_completions",
        limit_choices_to={"role": "student"},
    )
    lesson = models.ForeignKey(
        "courses.Lesson", on_delete=models.CASCADE, related_name="completions"
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "lesson"], name="unique_lesson_completion"),
        ]

    def __str__(self):
        return f"LessonCompletion(student={self.student_id}, lesson={self.lesson_id})"


class DailyMasterLog(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_master_logs",
        limit_choices_to={"role": "student"},
    )
    date = models.DateField()
    tasks_total = models.IntegerField(default=0)
    tasks_completed = models.IntegerField(default=0)
    level = models.IntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "date"], name="unique_daily_master_log"),
        ]

    def __str__(self):
        return f"DailyMasterLog(student={self.student_id}, date={self.date}, level={self.level})"

    @property
    def completion_percentage(self):
        if self.tasks_total == 0:
            return 0
        return int((self.tasks_completed / self.tasks_total) * 100)


class OTPRecord(models.Model):
    email = models.EmailField()
    otp_code = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["email", "created_at"]),
        ]

    def __str__(self):
        return f"OTPRecord(email={self.email}, used={self.is_used})"

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired


class RefreshToken(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_refresh_tokens",
        limit_choices_to={"role": "student"},
    )
    token = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)
    device_info = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["student", "is_revoked"]),
        ]

    def __str__(self):
        return f"RefreshToken(student={self.student_id}, revoked={self.is_revoked})"


class StudentNotification(models.Model):
    class Type(models.TextChoices):
        NEW_LESSON = "new_lesson", "New Lesson"
        NEW_QUIZ = "new_quiz", "New Quiz"
        NEW_ASSIGNMENT = "new_assignment", "New Assignment"
        DEADLINE_REMINDER = "deadline_reminder", "Deadline Reminder"
        FEEDBACK_RECEIVED = "feedback_received", "Feedback Received"
        GRADE_UPDATED = "grade_updated", "Grade Updated"
        QUIZ_PUBLISHED = "quiz_published", "Quiz Published"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_notification_records",
        limit_choices_to={"role": "student"},
    )
    type = models.CharField(max_length=30, choices=Type.choices)
    reference_type = models.CharField(max_length=30, blank=True, default="")
    reference_id = models.IntegerField(null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "type", "reference_id"],
                name="unique_student_notification",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"StudentNotification(student={self.student_id}, type={self.type}, read={self.is_read})"