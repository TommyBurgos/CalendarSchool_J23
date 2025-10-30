def rol_usuario(request):
    rol = getattr(getattr(request, "user", None), "rol", None)
    return {
        "ROL_NOMBRE": getattr(rol, "nombre", None)
    }
