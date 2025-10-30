# turnos/views_coordinador.py
from datetime import timedelta, datetime
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from user.decorators import requiere_roles
from .models import Cita, EstadoCita

from django.http import HttpResponse

TZ = timezone.get_current_timezone()

def _rango_semana(base_date):
    di = base_date - timedelta(days=base_date.weekday())  # lunes
    df = di + timedelta(days=6)                           # domingo
    return di, df


TZ = timezone.get_current_timezone()

def _parse_date(s: str):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def _rango_semana(base_date):
    di = base_date - timedelta(days=base_date.weekday())  # lunes
    df = di + timedelta(days=6)
    return di, df

def _aplicar_filtros(request, qs):
    """Aplica filtros GET: desde, hasta, estado, departamento. 
       Si es DocenteAdministrador, opcionalmente puedes limitar al departamento del usuario.
    """
    g = request.GET
    desde = _parse_date(g.get("desde", ""))
    hasta = _parse_date(g.get("hasta", ""))
    estado = (g.get("estado") or "").strip().upper()
    departamento = (g.get("departamento") or "").strip()

    if desde:
        qs = qs.filter(inicio__date__gte=desde)
    if hasta:
        qs = qs.filter(inicio__date__lte=hasta)
    if estado in dict(EstadoCita.choices):
        qs = qs.filter(estado=estado)
    if departamento:
        qs = qs.filter(docente__departamento__iexact=departamento)

    # Si deseas **forzar** que un DocenteAdministrador solo vea su departamento:
    if getattr(getattr(request.user, "rol", None), "nombre", None) == "DocenteAdministrador":
        dep_usuario = getattr(getattr(request.user, "perfil_docente", None), "departamento", "")
        if dep_usuario:
            qs = qs.filter(docente__departamento__iexact=dep_usuario)

    return qs

def _csv_desde_qs(qs):
    # Encabezados
    rows = ["inicio,fin,estado,docente,departamento,representante,estudiante,curso,motivo"]
    for c in qs:
        docente = c.docente.usuario.get_full_name() or c.docente.usuario.username
        depto = c.docente.departamento or ""
        rep = c.representante.get_full_name() or c.representante.username
        est = c.nombre_estudiante.replace(",", " ")
        mot = (c.motivo or "").replace("\n"," ").replace("\r"," ").replace(",", " ")
        rows.append(f"{c.inicio:%Y-%m-%d %H:%M},{c.fin:%H:%M},{c.estado},{docente},{depto},{rep},{est},{c.curso_estudiante},{mot}")
    return "\n".join(rows)

@requiere_roles("Administrador", "DocenteAdministrador")
def resumen_hoy(request):
    hoy = timezone.localdate()
    qs = (Cita.objects
          .filter(inicio__date=hoy)
          .select_related("docente__usuario", "representante")
          .order_by("inicio"))
    qs = _aplicar_filtros(request, qs)

    if request.GET.get("export") == "1":
        data = _csv_desde_qs(qs)
        resp = HttpResponse(data, content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="citas_hoy_{hoy}.csv"'
        return resp

    totales = dict(qs.values("estado").annotate(n=Count("id")).values_list("estado", "n"))
    ctx = {"titulo": "Resumen de Citas — Hoy", "rango": (hoy, hoy), "citas": qs, "totales": totales}
    return render(request, "resumen_coordinador.html", ctx)

@requiere_roles("Administrador", "DocenteAdministrador")
def resumen_semana(request):
    base = timezone.localdate()
    di, df = _rango_semana(base)
    qs = (Cita.objects
          .filter(inicio__date__range=(di, df))
          .select_related("docente__usuario", "representante")
          .order_by("inicio"))
    qs = _aplicar_filtros(request, qs)

    if request.GET.get("export") == "1":
        data = _csv_desde_qs(qs)
        resp = HttpResponse(data, content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="citas_semana_{di}_a_{df}.csv"'
        return resp

    totales = dict(qs.values("estado").annotate(n=Count("id")).values_list("estado", "n"))
    ctx = {"titulo": "Resumen de Citas — Semana", "rango": (di, df), "citas": qs, "totales": totales}
    return render(request, "resumen_coordinador.html", ctx)
