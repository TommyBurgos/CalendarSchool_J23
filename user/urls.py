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
