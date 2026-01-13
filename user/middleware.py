from django.shortcuts import redirect
from django.urls import reverse

class ForzarCambioPasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.user.debe_cambiar_password
            and request.path not in [
                reverse("cambiar_password_forzado"),
                reverse("logout"),
            ]
        ):
            return redirect("cambiar_password_forzado")

        return self.get_response(request)
