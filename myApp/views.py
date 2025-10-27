from django.shortcuts import render,redirect, get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render
from user.decorators import requiere_rol
from turnos.models import PerfilDocente, PerfilRepresentante, Cita, EstadoCita, ExcepcionDisponibilidad, TipoExcepcion

from django.contrib import messages
from django.views.decorators.http import require_POST

from user.decorators import requiere_rol
from turnos.models import (
    PerfilDocente, PerfilRepresentante, Cita, EstadoCita, ExcepcionDisponibilidad, TipoExcepcion, Cita, EstadoCita
)
from turnos.forms import FiltroCitasForm

import csv
from django.http import HttpResponse
from turnos.forms import FiltroCitasForm


# Create your views here.
def home(request):
    return render(request, 'sitioWeb/index.html')

def registro(request):
    return render(request, 'sitioWeb/sign-up.html')

@requiere_rol("Administrador")
def dashboard_admin(request):
    print("INICIE AL USUARIO ADMINISTRADOR.")
    tz = timezone.get_current_timezone()
    hoy = timezone.localdate()
    ahora = timezone.localtime(timezone.now(), tz)

    # Métricas superiores (igual que antes)
    docentes_activos = PerfilDocente.objects.filter(activo=True).count()
    reps = PerfilRepresentante.objects.count()

    citas_hoy_qs = Cita.objects.filter(inicio__date=hoy)
    total_hoy = citas_hoy_qs.count()
    pend_hoy = citas_hoy_qs.filter(estado=EstadoCita.PENDIENTE).count()
    conf_hoy = citas_hoy_qs.filter(estado=EstadoCita.CONFIRMADA).count()
    canc_hoy = citas_hoy_qs.filter(estado=EstadoCita.CANCELADA).count()

    bloqueos_hoy = ExcepcionDisponibilidad.objects.filter(fecha=hoy, tipo=TipoExcepcion.BLOQUEO).count()

    # Filtros (GET)
    form = FiltroCitasForm(request.GET or None)
    citas = Cita.objects.select_related("docente__usuario", "representante").order_by("inicio")

    if form.is_valid():
        fecha = form.cleaned_data.get("fecha")
        docente = form.cleaned_data.get("docente")
        estado = form.cleaned_data.get("estado")

        if fecha:
            citas = citas.filter(inicio__date=fecha)
        else:
            # Por defecto, muestra próximas 7 días
            desde = hoy
            hasta = hoy + timezone.timedelta(days=7)
            citas = citas.filter(inicio__date__range=(desde, hasta))

        if docente:
            citas = citas.filter(docente=docente)

        if estado:
            citas = citas.filter(estado=estado)
    else:
        # fallback si form inválido: próximas 7 días
        desde = hoy
        hasta = hoy + timezone.timedelta(days=7)
        citas = citas.filter(inicio__date__range=(desde, hasta))

    # Próximas 5 (para el widget)
    proximas = Cita.objects.filter(
        estado__in=[EstadoCita.PENDIENTE, EstadoCita.CONFIRMADA],
        inicio__gte=ahora
    ).order_by("inicio")[:5]

    context = {
        "docentes_activos": docentes_activos,
        "reps": reps,
        "total_hoy": total_hoy,
        "pend_hoy": pend_hoy,
        "conf_hoy": conf_hoy,
        "canc_hoy": canc_hoy,
        "bloqueos_hoy": bloqueos_hoy,
        "proximas": proximas,
        "hoy": hoy,
        "form": form,
        "citas": citas,
    }
    return render(request, "dashboard_admin.html", context)

# ------------------------
# Acciones rápidas
# ------------------------
@requiere_rol("Administrador")
@require_POST
def confirmar_cita_admin(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    if cita.estado == EstadoCita.CANCELADA:
        messages.error(request, "No puedes confirmar una cita cancelada.")
        return redirect(request.META.get("HTTP_REFERER", "dashboard_admin"))

    if cita.estado == EstadoCita.CONFIRMADA:
        messages.info(request, "La cita ya está confirmada.")
        return redirect(request.META.get("HTTP_REFERER", "dashboard_admin"))

    cita.estado = EstadoCita.CONFIRMADA
    # Si añadiste campos de auditoría, setéalos aquí (confirmada_por/en)
    cita.save(update_fields=["estado"])
    messages.success(request, "Cita confirmada.")
    return redirect(request.META.get("HTTP_REFERER", "dashboard_admin"))

@requiere_rol("Administrador")
@require_POST
def cancelar_cita_admin(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    if cita.estado == EstadoCita.CANCELADA:
        messages.info(request, "La cita ya estaba cancelada.")
        return redirect(request.META.get("HTTP_REFERER", "dashboard_admin"))

    motivo = (request.POST.get("motivo") or "").strip()
    cita.estado = EstadoCita.CANCELADA
    cita.cancelada_por = request.user
    cita.motivo_cancelacion = motivo[:255]
    cita.save(update_fields=["estado", "cancelada_por", "motivo_cancelacion"])
    messages.success(request, "Cita cancelada.")
    return redirect(request.META.get("HTTP_REFERER", "dashboard_admin"))
    
@requiere_rol("Administrador")
def exportar_citas_csv(request):
    # Reusar los filtros del dashboard
    hoy = timezone.localdate()
    form = FiltroCitasForm(request.GET or None)
    citas = Cita.objects.select_related("docente__usuario","representante").order_by("inicio")

    if form.is_valid():
        fecha = form.cleaned_data.get("fecha")
        docente = form.cleaned_data.get("docente")
        estado = form.cleaned_data.get("estado")
        if fecha:
            citas = citas.filter(inicio__date=fecha)
        else:
            desde, hasta = hoy, hoy + timezone.timedelta(days=7)
            citas = citas.filter(inicio__date__range=(desde, hasta))
        if docente:
            citas = citas.filter(docente=docente)
        if estado:
            citas = citas.filter(estado=estado)
    else:
        desde, hasta = hoy, hoy + timezone.timedelta(days=7)
        citas = citas.filter(inicio__date__range=(desde, hasta))

    # Armar CSV
    tz = timezone.get_current_timezone()
    filename = f"citas_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(resp)
    writer.writerow([
        "inicio", "fin", "estado", "docente", "representante_email",
        "estudiante_nombre", "curso", "motivo"
    ])
    for c in citas:
        ini = timezone.localtime(c.inicio, tz).strftime("%Y-%m-%d %H:%M")
        fin = timezone.localtime(c.fin, tz).strftime("%Y-%m-%d %H:%M")
        docente_nombre = (c.docente.usuario.get_full_name() or c.docente.usuario.username)
        writer.writerow([
            ini, fin, c.estado, docente_nombre, c.representante.email,
            c.nombre_estudiante, c.curso_estudiante, (c.motivo or "")[:150]
        ])
    return resp

@requiere_rol("Administrador")
def cita_detalle_admin(request, pk):
    c = get_object_or_404(
        Cita.objects.select_related("docente__usuario","representante","estudiante"),
        pk=pk
    )
    return render(request, "cita_detalle.html", {"c": c})

@requiere_rol("Administrador")
def agenda_global_admin(request):
    hoy = timezone.localdate()
    form = FiltroCitasForm(request.GET or None)
    qs = Cita.objects.select_related("docente__usuario","representante").order_by("inicio")

    if form.is_valid():
        fecha = form.cleaned_data.get("fecha")
        docente = form.cleaned_data.get("docente")
        estado = form.cleaned_data.get("estado")
        qs = qs.filter(inicio__date=fecha) if fecha else qs.filter(inicio__date__range=(hoy, hoy+timezone.timedelta(days=7)))
        if docente: qs = qs.filter(docente=docente)
        if estado: qs = qs.filter(estado=estado)
    else:
        qs = qs.filter(inicio__date__range=(hoy, hoy+timezone.timedelta(days=7)))

    paginator = Paginator(qs, 25)
    citas = paginator.get_page(request.GET.get("page"))
    return render(request, "agenda_global.html", {"form": form, "citas": citas})