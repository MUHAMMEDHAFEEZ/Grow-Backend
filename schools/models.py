from django.conf import settings
from django.db import models


class Grade(models.Model):
    name = models.CharField(max_length=100)
    level = models.IntegerField()
    stage = models.CharField(max_length=20)
    school = models.ForeignKey(
        "School", on_delete=models.CASCADE, null=True, blank=True, related_name="grades"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "درجة"
        verbose_name_plural = "الدرجات"


class School(models.Model):
    name = models.CharField(max_length=255)
    school_code = models.CharField(max_length=50, unique=True)
    school_type = models.CharField(max_length=20, choices=[
        ('arabic', 'عربي'),
        ('language', 'لغات')
    ])
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.school_code})"


class RegistrationCode(models.Model):
    class CodeType(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"

    code = models.CharField(max_length=20, unique=True)
    school = models.ForeignKey(
        "School", on_delete=models.CASCADE, related_name="registration_codes"
    )
    grade = models.ForeignKey(
        "Grade", on_delete=models.CASCADE, null=True, blank=True, related_name="registration_codes"
    )
    code_type = models.CharField(max_length=10, choices=CodeType.choices)
    is_used = models.BooleanField(default=False)
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["school", "code_type", "is_used"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        return f"RegistrationCode({self.code}, {self.code_type}, used={self.is_used})"


class Subject(models.Model):
    name_ar = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100, blank=True)
    code = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.name_ar} ({self.code})"


class Course(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="courses")
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="courses")
    
    school_type = models.CharField(max_length=10, choices=[
        ('arabic', 'عربي'),
        ('language', 'لغات'),
    ], default='arabic')

    section = models.CharField(max_length=20, choices=[
        ('general', 'عام'),
        ('literary', 'أدبي'),
        ('scientific', 'علمي'),
    ], blank=True, null=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        section_str = f" - {self.get_section_display()}" if self.section else ""
        return f"{self.subject.name_ar} | {self.grade.name} | {self.get_school_type_display()}{section_str}"

    class Meta:
        unique_together = ('subject', 'grade', 'school_type', 'section')