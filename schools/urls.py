from django.urls import path

from schools.views import GradeListView, SchoolListView, school_login_view, school_student_list_view
from schools.views.class_views import class_detail_view

urlpatterns = [
    path("grades/", GradeListView.as_view(), name="grade-list"),
    path("login/", school_login_view, name="school-login"),
    path("students/", school_student_list_view, name="school-student-list"),
    path("classes/<int:class_id>/", class_detail_view, name="class-detail"),
    path("", SchoolListView.as_view(), name="school-list"),
]
