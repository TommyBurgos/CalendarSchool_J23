# turnos/emailing.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.apps import apps
from typing import List

def enviar_notificacion(asunto: str, template: str, contexto: dict, destinatarios: List[str]):
    """Envía email HTML + texto plano. Ignora destinatarios vacíos."""
    # Filtrar emails vacíos o None
    destinatarios = [e for e in (destinatarios or []) if e]
    if not destinatarios:
        return  # nada que enviar

    html = render_to_string(template, contexto)
    texto = strip_tags(html)

    send_mail(
        subject=asunto,
        message=texto,
        from_email=None,  # usa DEFAULT_FROM_EMAIL de settings
        recipient_list=destinatarios,
        html_message=html,
        fail_silently=False,
    )
from user.models import User

def obtener_emails_admins() -> List[str]:
    """
    Devuelve emails de usuarios con rol 'Administrador' activos.
    Compatible con AUTH_USER_MODEL personalizado.
    """
    User = apps.get_model(settings.AUTH_USER_MODEL)  # evita import circular
    return list(
        User.objects.filter(rol__nombre="Administrador", is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )
