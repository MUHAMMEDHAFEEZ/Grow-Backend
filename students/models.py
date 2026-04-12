from django.db import models
from django.contrib.auth import get_user_model
from schools.models import School, Grade   # ← استيراد Grade من schools

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

    full_name = models.CharField(max_length=150)
    school_code = models.CharField(max_length=50, blank=True, null=True)

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
            
            # حلقة للتأكد من عدم التكرار
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