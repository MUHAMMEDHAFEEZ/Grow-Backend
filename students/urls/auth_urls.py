from django.urls import path

from students.views.auth_views import (
    reset_password_view,
    send_otp_view,
    student_login_view,
    student_logout_view,
    student_signup_view,
    student_token_refresh_view,
    verify_otp_view,
)

urlpatterns = [
    path("signup/", student_signup_view, name="student_signup"),
    path("login/", student_login_view, name="student_login"),
    path("token/refresh/", student_token_refresh_view, name="student_token_refresh"),
    path("logout/", student_logout_view, name="student_logout"),
    path("otp/send/", send_otp_view, name="student_otp_send"),
    path("otp/verify/", verify_otp_view, name="student_otp_verify"),
    path("password/reset/", reset_password_view, name="student_password_reset"),
]
