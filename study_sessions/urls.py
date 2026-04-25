from django.urls import path
from study_sessions import views


urlpatterns = [
    path("start/", views.SessionStartView.as_view(), name="session-start"),
    path("end/", views.SessionEndView.as_view(), name="session-end"),
    path("active/", views.SessionActiveView.as_view(), name="session-active"),
    path("total/", views.SessionTotalView.as_view(), name="session-total"),
    path("", views.SessionListView.as_view(), name="session-list"),
]
