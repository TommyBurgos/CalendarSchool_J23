from django.shortcuts import redirect
from django.contrib import messages

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
