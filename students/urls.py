from django.urls import path
from .views import add_student, check_has_students, get_grades, get_schools, get_students   # ← أضف check_has_students لو عملته

urlpatterns = [
    path('add-student/', add_student, name='add_student'),
    path('check-has-students/', check_has_students, name='check_has_students'),
    path('schools/', get_schools, name='get_schools'),
    path('grades/', get_grades, name='get_grades'),
    path('students/', get_students, name='get_students'),  # ← أضف endpoint جديد للطلاب
]