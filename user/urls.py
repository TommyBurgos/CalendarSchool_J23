from django.urls import path
from . import views

urlpatterns = [
    path("registrarse/", views.registrar, name="registrar"),
    path("login/", views.vista_login, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("mi-perfil/", views.mi_perfil, name="mi_perfil"),
    path("cambiar-password/", views.cambiar_password, name="cambiar_password"),
    path("cambiar-password/forzado/", views.cambiar_password_forzado, name="cambiar_password_forzado"),

]

from django.contrib.auth import views as auth_views

urlpatterns += [
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="user/password_reset.html"
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="user/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="user/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="user/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]

