from django.urls import path
from .views import GradeListView, GradeSubmissionView, StudentGPAView

urlpatterns = [
    path("grades/", GradeListView.as_view(), name="grade-list"),
    path("submissions/<int:submission_pk>/grade/", GradeSubmissionView.as_view(), name="grade-submission"),
    path("grades/student/<int:student_id>/gpa/", StudentGPAView.as_view(), name="student-gpa"),
]
