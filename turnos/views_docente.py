# turnos/views_docente.py
from datetime import datetime, timedelta
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from user.decorators import requiere_rol
from .models import PerfilDocente, DisponibilidadSemanal, ExcepcionDisponibilidad, Cita
from .forms import DisponibilidadSemanalForm, ExcepcionDisponibilidadForm
from .services import generar_slots
from user.decorators import requiere_roles

@requiere_roles("Docente", "DocenteAdministrador")
def dashboard_docente(request):
    print("INICIE AL USUARIO DOCENTE.")
    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")    
    hoy = timezone.localdate()
    citas_hoy = Cita.objects.filter(docente=docente, inicio__date=hoy).order_by("inicio")
    return render(request, "docente/dashboard.html", {
        "docente": docente,
        "citas_hoy": citas_hoy,
    })

# -------- Disponibilidad semanal --------
@requiere_roles("Docente", "DocenteAdministrador")
def disponibilidad_list(request):
    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")
    items = DisponibilidadSemanal.objects.filter(docente=docente).order_by("dia_semana","hora_inicio")
    return render(request, "docente/disponibilidad_list.html", {"items": items})

@requiere_roles("Docente", "DocenteAdministrador")
def disponibilidad_create(request):
    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")
    if request.method == "POST":
        form = DisponibilidadSemanalForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.docente = docente
            try:
                obj.full_clean()
                obj.save()
                messages.success(request, "Disponibilidad guardada.")
                return redirect("disp_list")
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = DisponibilidadSemanalForm()
    return render(request, "docente/disponibilidad_form.html", {"form": form})

@requiere_roles("Docente", "DocenteAdministrador")
def disponibilidad_delete(request, pk):
    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")
    obj = get_object_or_404(DisponibilidadSemanal, pk=pk, docente=docente)
    if request.method == "POST":
        obj.delete()
        messages.info(request, "Disponibilidad eliminada.")
        return redirect("disp_list")
    return render(request, "confirm_delete.html", {"obj": obj})

# -------- Excepciones (EXTRA / BLOQUEO) --------
@requiere_roles("Docente", "DocenteAdministrador")
def excepciones_list(request):
    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")
    items = ExcepcionDisponibilidad.objects.filter(docente=docente).order_by("-fecha","hora_inicio")
    return render(request, "docente/excepciones_list.html", {"items": items})

@requiere_roles("Docente", "DocenteAdministrador")
def excepciones_create(request):
    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")
    if request.method == "POST":
        form = ExcepcionDisponibilidadForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.docente = docente
            try:
                obj.full_clean()
                obj.save()
                messages.success(request, "Excepción registrada.")
                return redirect("exc_list")
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = ExcepcionDisponibilidadForm()
    return render(request, "docente/excepciones_form.html", {"form": form})

@requiere_roles("Docente", "DocenteAdministrador")
def excepciones_delete(request, pk):
    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")
    obj = get_object_or_404(ExcepcionDisponibilidad, pk=pk, docente=docente)
    if request.method == "POST":
        obj.delete()
        messages.info(request, "Excepción eliminada.")
        return redirect("exc_list")
    return render(request, "confirm_delete.html", {"obj": obj})

# -------- Agenda --------
@requiere_roles("Docente", "DocenteAdministrador")
def agenda_dia(request):
    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")
    fecha_str = request.GET.get("fecha")
    fecha = timezone.localdate() if not fecha_str else datetime.strptime(fecha_str, "%Y-%m-%d").date()
    starts = generar_slots(docente, fecha)  # datetimes aware de inicio
    citas = Cita.objects.filter(docente=docente, inicio__date=fecha).order_by("inicio")
    # armar pares (inicio, fin) usando minutos_del_docente
    minuto = docente.minutos_por_bloque or 20
    slots = [(s, s + timezone.timedelta(minutes=minuto)) for s in starts]
    return render(request, "docente/agenda_dia.html", {
        "fecha": fecha, "slots": slots, "citas": citas
    })

@requiere_roles("Docente", "DocenteAdministrador")
def agenda_semana(request):
    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")
    base = timezone.localdate()
    di = base - timezone.timedelta(days=base.weekday())
    dias = [di + timezone.timedelta(days=i) for i in range(7)]
    minuto = docente.minutos_por_bloque or 20
    data = []
    for d in dias:
        starts = generar_slots(docente, d)
        slots = [(s, s + timezone.timedelta(minutes=minuto)) for s in starts]
        citas = Cita.objects.filter(docente=docente, inicio__date=d).order_by("inicio")
        data.append((d, slots, citas))
    return render(request, "docente/agenda_semana.html", {"data": data, "di": di})

# turnos/views_docente.py (añade)
from django.views.decorators.http import require_POST
from .models import EstadoCita

@requiere_roles("Docente", "DocenteAdministrador")
@require_POST
def cita_confirmar(request, pk):
    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")
    c = get_object_or_404(Cita, pk=pk, docente=docente)
    c.estado = EstadoCita.CONFIRMADA
    c.full_clean(); c.save()
    messages.success(request, "Cita confirmada.")
    return redirect(request.META.get("HTTP_REFERER", "turnos:agenda_dia"))

@requiere_roles("Docente", "DocenteAdministrador")
def cita_cancelar(request, pk):
    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")
    c = get_object_or_404(Cita, pk=pk, docente=docente)
    if request.method == "POST":
        motivo = (request.POST.get("motivo") or "").strip()
        c.estado = EstadoCita.CANCELADA
        c.cancelada_por = request.user
        c.motivo_cancelacion = motivo[:255]
        c.full_clean(); c.save()
        messages.info(request, "Cita cancelada.")
        return redirect(request.META.get("HTTP_REFERER", "turnos:agenda_dia"))
    return render(request, "turnos/docente/cita_cancelar_confirm.html", {"cita": c})
