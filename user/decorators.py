from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def requiere_rol(nombre_rol):
    def wrapper(view_func):
        def _wrapped(request, *args, **kwargs):
            u = request.user
            if not u.is_authenticated:
                messages.error(request, "Debes iniciar sesión.")
                return redirect("login")
            if not getattr(u, "rol", None) or (u.rol and u.rol.nombre != nombre_rol):
                messages.error(request, "No tienes permisos para ver esta sección.")
                return redirect("dashboard")  # o a donde prefieras
            return view_func(request, *args, **kwargs)
        return _wrapped
    return wrapper

def requiere_roles(*nombres):
    nombres = set(nombres)
    def wrapper(view):
        @wraps(view)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Debes iniciar sesión.")
                return redirect("login")
            rol = getattr(request.user, "rol", None)
            if not rol or rol.nombre not in nombres:
                messages.error(request, "No tienes permiso para acceder a esta sección.")
                return redirect("mi_perfil")
            return view(request, *args, **kwargs)
        return _wrapped
    return wrapper