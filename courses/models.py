from django.conf import settings
from django.db import models
from django.utils import timezone


class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="taught_courses",
        limit_choices_to={"role": "teacher"},
    )
    grade = models.ForeignKey(
        "schools.Grade",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="course_list",
    )
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    target_capacity = models.PositiveIntegerField(
        default=35, help_text="Target maximum enrollment"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class StudentCourse(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="student_courses"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_courses",
        limit_choices_to={"role": "student"},
    )
    is_active = models.BooleanField(default=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "student")
        indexes = [
            models.Index(fields=["course", "is_active"]),
        ]
        ordering = ["enrolled_at"]
        verbose_name = "Student Course"

    def __str__(self) -> str:
        return f"{self.student.username} in {self.course.title}"


class CourseProgress(models.Model):
    class CompletionStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_progress",
        limit_choices_to={"role": "student"},
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="course_progress"
    )
    progress_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00
    )
    study_time_seconds = models.IntegerField(default=0)
    last_activity = models.DateTimeField(null=True, blank=True)
    completion_status = models.CharField(
        max_length=20,
        choices=CompletionStatus.choices,
        default=CompletionStatus.NOT_STARTED,
    )

    class Meta:
        unique_together = ("student", "course")
        indexes = [
            models.Index(fields=["course", "completion_status"]),
        ]

    def __str__(self) -> str:
        return f"{self.student.username} — {self.course.title} ({self.completion_status})"


class Lesson(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=255)
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    video_url = models.URLField(blank=True, default="")
    pdf_file = models.FileField(upload_to="lesson_pdfs/", blank=True)
    resources = models.FileField(upload_to="lesson_resources/", blank=True)
    xp_reward = models.PositiveIntegerField(default=0)
    bonus_xp = models.PositiveIntegerField(default=0)
    start_time = models.DateTimeField(
        null=True, blank=True, help_text="Scheduled lesson start time"
    )
    end_time = models.DateTimeField(
        null=True, blank=True, help_text="Scheduled lesson end time"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return f"{self.course.title} — {self.title}"


class LessonActivity(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_activities",
        limit_choices_to={"role": "student"},
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="lesson_activities"
    )
    watch_duration_seconds = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    last_opened_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "lesson")
        indexes = [
            models.Index(fields=["lesson", "completed"]),
        ]
        verbose_name = "Lesson Activity"
        verbose_name_plural = "Lesson Activities"

    def __str__(self) -> str:
        return f"{self.student.username} — {self.lesson.title} (watched {self.watch_duration_seconds}s)"


class Quiz(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="quizzes"
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name="quizzes"
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_quizzes",
        limit_choices_to={"role": "teacher"},
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    duration_minutes = models.PositiveIntegerField(default=30)
    xp_reward = models.PositiveIntegerField(default=0)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["course"]),
            models.Index(fields=["lesson"]),
            models.Index(fields=["teacher"]),
        ]
        verbose_name_plural = "Quizzes"

    def __str__(self) -> str:
        return f"{self.course.title} — {self.title}"


class QuizAttempt(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
        limit_choices_to={"role": "student"},
    )
    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="attempts"
    )
    score = models.DecimalField(max_digits=5, decimal_places=2)
    attempt_number = models.IntegerField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "quiz", "attempt_number")
        indexes = [
            models.Index(fields=["student", "quiz", "-attempt_number"]),
            models.Index(fields=["quiz"]),
        ]
        ordering = ["-attempt_number"]

    def __str__(self) -> str:
        return f"{self.student.username} attempt #{self.attempt_number} on {self.quiz.title}"


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return f"Q{self.order}: {self.text[:50]}"


class AnswerOption(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="options"
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.text


class QuizSubmission(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="quiz_submissions"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_submissions",
        limit_choices_to={"role": "student"},
    )
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    raw_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    normalized_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    xp_earned = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS
    )

    class Meta:
        unique_together = ("quiz", "student")
        indexes = [
            models.Index(fields=["quiz", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.student.username} → {self.quiz.title} ({self.status})"

