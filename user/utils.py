from user.models import Institucion

def get_institucion_activa(request):
    inst_id = request.session.get("institucion_id")
    if inst_id:
        return Institucion.objects.filter(id=inst_id, activo=True).first()
    # fallback: la institución del usuario
    return getattr(request.user, "institucion", None)
