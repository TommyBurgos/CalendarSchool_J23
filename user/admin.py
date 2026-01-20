from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User
from .forms import UsuarioCreationForm, UsuarioChangeForm


@admin.register(User)  # ✅ usa SOLO esta línea
class UserAdmin(BaseUserAdmin):
    add_form = UsuarioCreationForm
    form = UsuarioChangeForm
    model = User

    list_display = (
        "email",
        "cedula",
        "username",
        "rol",
        "institucion",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "rol",
        "institucion",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    # ❗ CORREGIDO: ForeignKey → usar __campo
    search_fields = (
        "email",
        "cedula",
        "username",
        "first_name",
        "last_name",
        "rol__nombre",
        "institucion__nombre",
    )

    ordering = ("email",)

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "cedula",
                "first_name",
                "last_name",
                "rol",
                "institucion",
                "is_active",
                "password1",
                "password2",
            ),
        }),
    )

    fieldsets = (
        (None, {
            "fields": (
                "email",
                "username",
                "password",
            )
        }),
        ("Información personal", {
            "fields": (
                "cedula",
                "first_name",
                "last_name",
            )
        }),("Control de sesión", {
            "fields": (
                "debe_cambiar_password",  # ✅ EDITABLE AQUÍ
            )
        }),
        ("Rol y estado", {
            "fields": (
                "rol",
                "institucion",
                "is_active",
                "is_staff",
                "is_superuser",
            )
        }),
        ("Permisos", {
            "fields": (
                "groups",
                "user_permissions",
            )
        }),
        ("Cambiar contraseña", {
            "fields": (
                "password1",
                "password2",
            )
        }),
    )

    readonly_fields = ("username",)
