from django.urls import path

from schools.views import GradeListView

urlpatterns = [
    path("grades/", GradeListView.as_view(), name="grade-list"),
]
