from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    EnrollmentCodeListView,
    GenerateCodesView,
    ParentProfileView,
    RevokeCodeView,
    UseCodeView,
    change_password_view,
    forgot_password_view,
    login,
    logout,
    me,
    profile,
    register,
    reset_password_view,
    school_view,
)

urlpatterns = [
    # Auth
    path("register/",         register,               name="auth-register"),
    path("login/",            login,                  name="auth-login"),
    path("logout/",           logout,                 name="auth-logout"),
    path("token/refresh/",    TokenRefreshView.as_view(), name="token-refresh"),

    # Password management
    path("forgot-password/",  forgot_password_view,   name="auth-forgot-password"),
    path("reset-password/",   reset_password_view,    name="auth-reset-password"),
    path("change-password/",  change_password_view,   name="auth-change-password"),

    # Profile
    path("profile/",          profile,                name="auth-profile"),
    path("me/",               me,                     name="auth-me"),

    # Parent
    path("parent-profile/",   ParentProfileView.as_view(), name="parent-profile"),

    # School admin
    path("school/",           school_view,            name="auth-school"),

    # Enrollment codes
    path("enrollment-codes/use/",                                                    UseCodeView.as_view(),          name="enrollment-code-use"),
    path("schools/<int:school_id>/enrollment-codes/",                                EnrollmentCodeListView.as_view(), name="enrollment-codes-list"),
    path("schools/<int:school_id>/enrollment-codes/generate/",                       GenerateCodesView.as_view(),    name="enrollment-codes-generate"),
    path("schools/<int:school_id>/enrollment-codes/<int:code_id>/revoke/",           RevokeCodeView.as_view(),       name="enrollment-code-revoke"),
]
