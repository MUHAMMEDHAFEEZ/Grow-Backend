from django.urls import path

from students.views.assignment_views import assignment_detail_view, assignment_submit_view
from students.views.course_views import complete_lesson_view, student_course_detail_view, student_course_list_view
from students.views.dashboard_views import student_dashboard_view
from students.views.notification_views import mark_notification_read_view, notification_list_view
from students.views.quiz_views import start_quiz_view, submit_quiz_view
from students.views.settings_views import student_settings_view
from students.views.task_views import student_tasks_view

urlpatterns = [
    path("dashboard/", student_dashboard_view, name="student_dashboard"),
    path("courses/", student_course_list_view, name="student_course_list"),
    path("courses/<int:course_id>/", student_course_detail_view, name="student_course_detail"),
    path("lessons/<int:lesson_id>/complete/", complete_lesson_view, name="complete_lesson"),
    path("quizzes/<int:quiz_id>/start/", start_quiz_view, name="start_quiz"),
    path("quizzes/<int:quiz_id>/submit/", submit_quiz_view, name="submit_quiz"),
    path("assignments/<int:assignment_id>/", assignment_detail_view, name="assignment_detail"),
    path("assignments/<int:assignment_id>/submit/", assignment_submit_view, name="assignment_submit"),
    path("tasks/", student_tasks_view, name="student_tasks"),
    path("notifications/", notification_list_view, name="notification_list"),
    path("notifications/<int:notification_id>/read/", mark_notification_read_view, name="mark_notification_read"),
    path("settings/", student_settings_view, name="student_settings"),
]
