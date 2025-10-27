# turnos/views_slots.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils.dateparse import parse_date
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import PerfilDocente
from .services import generar_slots

@require_GET
def api_slots(request):
    docente_id = request.GET.get("docente_id")
    fecha_str = request.GET.get("fecha")

    if not docente_id or not fecha_str:
        return JsonResponse({"ok": False, "error": "Parámetros requeridos: docente_id, fecha (YYYY-MM-DD)."}, status=400)

    fecha = parse_date(fecha_str)
    if not fecha:
        return JsonResponse({"ok": False, "error": "Fecha inválida. Use YYYY-MM-DD."}, status=400)

    docente = get_object_or_404(PerfilDocente, pk=docente_id, activo=True)

    slots = generar_slots(docente, fecha)  # datetimes aware
    # Formato ISO local (America/Guayaquil)
    tz = timezone.get_current_timezone()
    data = [timezone.localtime(s, tz).strftime("%Y-%m-%d %H:%M") for s in slots]

    return JsonResponse({
        "ok": True,
        "docente_id": docente.id,
        "fecha": fecha_str,
        "minutos_por_bloque": docente.minutos_por_bloque,
        "slots": data
    })
