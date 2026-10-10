from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import PlacifyPasswordResetForm

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("logout/", views.PlacifyLogoutView.as_view(), name="logout"),
    # Replaces legacy forgot_password.php, which generated a reset token but
    # had no page to consume it (see docs/LEGACY_ARCHITECTURE.md). Django's
    # built-in views provide a complete, working, signed-token flow.
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/password_reset_email.txt",
            subject_template_name="accounts/password_reset_subject.txt",
            form_class=PlacifyPasswordResetForm,
            success_url="/accounts/password-reset/done/",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url="/accounts/reset/done/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
