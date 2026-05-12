from django.urls import path

from .views import (
    assignment_views,
    auth_views,
    course_views,
    dashboard_views,
    notification_views,
    quiz_views,
    settings_views,
    student_views,
)

urlpatterns = [
    # Auth
    path("auth/signup/", auth_views.signup, name="teacher-signup"),
    path("auth/login/", auth_views.login, name="teacher-login"),
    path("auth/refresh/", auth_views.refresh, name="teacher-refresh"),
    path("auth/logout/", auth_views.logout, name="teacher-logout"),
    path("auth/forgot-password/send-otp/", auth_views.send_otp_view, name="teacher-send-otp"),
    path("auth/forgot-password/verify-otp/", auth_views.verify_otp_view, name="teacher-verify-otp"),
    path("auth/forgot-password/reset/", auth_views.reset_password_view, name="teacher-reset-password"),
    # Dashboard
    path("dashboard/", dashboard_views.dashboard, name="teacher-dashboard"),
    # Courses
    path("courses/", course_views.list_courses, name="teacher-course-list"),
    path("courses/create/", course_views.create_course, name="teacher-course-create"),
    path("courses/<int:course_id>/", course_views.get_course, name="teacher-course-detail"),
    path("courses/<int:course_id>/update/", course_views.update_course, name="teacher-course-update"),
    path("courses/<int:course_id>/delete/", course_views.delete_course, name="teacher-course-delete"),
    # Lessons
    path("courses/<int:course_id>/lessons/", course_views.list_lessons, name="teacher-lesson-list"),
    path("courses/<int:course_id>/lessons/create/", course_views.create_lesson, name="teacher-lesson-create"),
    path("lessons/<int:lesson_id>/", course_views.get_lesson_view, name="teacher-lesson-detail"),
    path("lessons/<int:lesson_id>/update/", course_views.update_lesson, name="teacher-lesson-update"),
    path("lessons/<int:lesson_id>/delete/", course_views.delete_lesson, name="teacher-lesson-delete"),
    # Assignments
    path("assignments/", assignment_views.list_assignments, name="teacher-assignment-list"),
    path("assignments/create/", assignment_views.create_assignment, name="teacher-assignment-create"),
    path("assignments/<int:assignment_id>/", assignment_views.get_assignment, name="teacher-assignment-detail"),
    path("assignments/<int:assignment_id>/update/", assignment_views.update_assignment, name="teacher-assignment-update"),
    path("assignments/<int:assignment_id>/delete/", assignment_views.delete_assignment, name="teacher-assignment-delete"),
    path("assignments/<int:assignment_id>/review/", assignment_views.review_panel, name="teacher-assignment-review"),
    path("submissions/<int:submission_id>/grade/", assignment_views.grade_submission_view, name="teacher-grade-submission"),
    # Quizzes
    path("quizzes/", quiz_views.list_quizzes, name="teacher-quiz-list"),
    path("quizzes/create/", quiz_views.create_quiz, name="teacher-quiz-create"),
    path("quizzes/<int:quiz_id>/", quiz_views.get_quiz, name="teacher-quiz-detail"),
    path("quizzes/<int:quiz_id>/update/", quiz_views.update_quiz, name="teacher-quiz-update"),
    path("quizzes/<int:quiz_id>/results/", quiz_views.quiz_results, name="teacher-quiz-results"),
    path("quizzes/<int:quiz_id>/feedback/", quiz_views.send_feedback, name="teacher-quiz-feedback"),
    # Students
    path("students/", student_views.list_students, name="teacher-student-list"),
    # Settings
    path("settings/profile/", settings_views.get_profile, name="teacher-profile"),
    path("settings/profile/update/", settings_views.update_profile, name="teacher-profile-update"),
    path("settings/notifications/", settings_views.get_notification_prefs, name="teacher-notification-prefs"),
    path("settings/notifications/update/", settings_views.update_notification_prefs, name="teacher-notification-prefs-update"),
    # Notifications
    path("notifications/", notification_views.list_notifications, name="teacher-notification-list"),
    path("notifications/<int:notification_id>/read/", notification_views.mark_read, name="teacher-notification-read"),
]
