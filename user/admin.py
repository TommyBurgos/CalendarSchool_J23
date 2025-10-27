from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User
from .forms import UsuarioCreationForm, UsuarioChangeForm

@admin.register(User)  # ✅ usa SOLO esta línea, sin admin.site.register al final
class UserAdmin(BaseUserAdmin):
    add_form = UsuarioCreationForm
    form = UsuarioChangeForm
    model = User

    list_display = ("email", "cedula", "username", "rol", "is_active", "is_staff")
    list_filter  = ("rol", "is_active", "is_staff", "is_superuser")
    search_fields = ("email", "cedula", "first_name", "last_name", "username")
    ordering = ("email",)

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "cedula", "first_name", "last_name", "rol", "is_active", "password1", "password2"),
        }),
    )
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),  # username solo-lectura en el form (viene del modelo)
        ("Información personal", {"fields": ("cedula", "first_name", "last_name")}),
        ("Rol y estado", {"fields": ("rol", "is_active", "is_staff", "is_superuser")}),
        ("Permisos", {"fields": ("groups", "user_permissions")}),
        ("Cambiar contraseña", {"fields": ("password1", "password2")}),
    )
    readonly_fields = ("username",)  # se rellena desde cédula automáticamente

