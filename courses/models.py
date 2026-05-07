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
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=255)
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)
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
    title = models.CharField(max_length=255)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["course"]),
            models.Index(fields=["lesson"]),
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


