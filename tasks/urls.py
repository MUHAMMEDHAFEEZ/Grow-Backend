from django.urls import path

from .views import CompleteTaskView, PendingTasksView, StudentTaskListView, TaskSummaryView

urlpatterns = [
    path("tasks/", StudentTaskListView.as_view(), name="task-list"),
    path("tasks/pending/", PendingTasksView.as_view(), name="task-pending"),
    path("tasks/<int:pk>/complete/", CompleteTaskView.as_view(), name="task-complete"),
    path("courses/<int:course_id>/task-summary/", TaskSummaryView.as_view(), name="task-summary"),
]
