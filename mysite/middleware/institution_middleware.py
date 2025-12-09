from django.shortcuts import redirect
from user.models import Institucion

class InstitucionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Si ya hay institución en sesión, seguimos
        if request.user.is_authenticated:
            inst = getattr(request.user, "institucion", None)
            if inst:
                request.institucion = inst
            else:
                request.institucion = None

        return self.get_response(request)
