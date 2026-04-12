from django.db import models

class Grade(models.Model):
    name = models.CharField(max_length=100)
    level = models.IntegerField()
    stage = models.CharField(max_length=20)

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