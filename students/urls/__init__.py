from django.urls import path
from students.views import check_has_students, get_grades, get_schools, get_students, dashboard

urlpatterns = [
    path('check-has-students/', check_has_students, name='check_has_students'),
    path('schools/', get_schools, name='get_schools'),
    path('grades/', get_grades, name='get_grades'),
    path('students/', get_students, name='get_students'),
    path('dashboard/', dashboard, name='dashboard'),
]