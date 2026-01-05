# turnos/views_docente.py
from datetime import datetime, timedelta,date
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from user.decorators import requiere_rol
from .models import PerfilDocente, DisponibilidadSemanal, ExcepcionDisponibilidad, Cita, ComentarioCita
from .forms import DisponibilidadSemanalForm, ExcepcionDisponibilidadForm, ComentarioCitaForm, NuevoComentarioCitaForm
from django.core.exceptions import PermissionDenied

from .services import generar_slots
from user.decorators import requiere_roles

from calendar import monthrange


@requiere_roles("Docente", "DocenteAdministrador")
def dashboard_docente(request):
    print("INICIE AL USUARIO DOCENTE.")
    inst = request.user.institucion

    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        institucion=inst,
        defaults={"minutos_por_bloque": 20, "activo": True}
    )

    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")    
    hoy = timezone.localdate()
    citas_hoy = Cita.objects.filter(docente=docente, inicio__date=hoy, institucion=inst).order_by("inicio")
    return render(request, "docente/dashboard.html", {
        "docente": docente,
        "citas_hoy": citas_hoy,
    })

# -------- Disponibilidad semanal --------
@requiere_roles("Docente", "DocenteAdministrador")
def disponibilidad_list(request):
    inst = request.user.institucion
    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")
    items = DisponibilidadSemanal.objects.filter(docente=docente, institucion=inst).order_by("dia_semana","hora_inicio")
    return render(request, "docente/disponibilidad_list.html", {"items": items})

@requiere_roles("Docente", "DocenteAdministrador")
def disponibilidad_create(request):
    inst = request.user.institucion
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
            obj.institucion = inst
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
    inst = request.user.institucion
    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")
    obj = get_object_or_404(DisponibilidadSemanal, pk=pk, docente=docente, institucion=inst)

    if request.method == "POST":
        obj.delete()
        messages.info(request, "Disponibilidad eliminada.")
        return redirect("disp_list")
    return render(request, "confirm_delete.html", {"obj": obj})

# -------- Excepciones (EXTRA / BLOQUEO) --------
@requiere_roles("Docente", "DocenteAdministrador")
def excepciones_list(request):
    inst = request.user.institucion
    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")
    items = ExcepcionDisponibilidad.objects.filter(docente=docente, institucion=inst).order_by("-fecha","hora_inicio")
    return render(request, "docente/excepciones_list.html", {"items": items})

@requiere_roles("Docente", "DocenteAdministrador")
def excepciones_create(request):
    inst = request.user.institucion
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
            obj.institucion = inst
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
    inst = request.user.institucion
    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")
    obj = get_object_or_404(ExcepcionDisponibilidad, pk=pk, docente=docente, institucion=inst)
    if request.method == "POST":
        obj.delete()
        messages.info(request, "Excepción eliminada.")
        return redirect("exc_list")
    return render(request, "confirm_delete.html", {"obj": obj})

# -------- Agenda --------
@requiere_roles("Docente", "DocenteAdministrador")
def agenda_dia(request):
    inst = request.user.institucion

    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        institucion=inst,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")

    fecha_str = request.GET.get("fecha")
    fecha = timezone.localdate() if not fecha_str else datetime.strptime(fecha_str, "%Y-%m-%d").date()

    starts = generar_slots(docente, fecha)

    citas = Cita.objects.filter(
        docente=docente,
        institucion=inst,
        inicio__date=fecha
    ).order_by("inicio")

    minuto = docente.minutos_por_bloque or 20
    slots = [(s, s + timezone.timedelta(minutes=minuto)) for s in starts]

    return render(request, "docente/agenda_dia.html", {
        "fecha": fecha,
        "slots": slots,
        "citas": citas
    })

@requiere_roles("Docente", "DocenteAdministrador")
def agenda_semana(request):
    inst = request.user.institucion

    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        institucion=inst,
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

        citas = Cita.objects.filter(
            docente=docente,
            institucion=inst,
            inicio__date=d
        ).order_by("inicio")

        data.append((d, slots, citas))

    return render(request, "docente/agenda_semana.html", {"data": data, "di": di})

# turnos/views_docente.py (añade)
from django.views.decorators.http import require_POST
from .models import EstadoCita
@requiere_roles("Docente", "DocenteAdministrador")
@require_POST
def cita_confirmar(request, pk):
    inst = request.user.institucion

    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        institucion=inst,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")

    c = get_object_or_404(Cita, pk=pk, docente=docente, institucion=inst)

    c.estado = EstadoCita.CONFIRMADA
    c.full_clean()
    c.save()

    messages.success(request, "Cita confirmada.")
    return redirect(request.META.get("HTTP_REFERER", "turnos:agenda_dia"))


@requiere_roles("Docente", "DocenteAdministrador")
def cita_cancelar(request, pk):
    inst = request.user.institucion

    docente, creado = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        institucion=inst,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )
    if creado:
        messages.info(request, "Se creó tu perfil de docente con valores por defecto.")

    c = get_object_or_404(Cita, pk=pk, docente=docente, institucion=inst)

    if request.method == "POST":
        motivo = (request.POST.get("motivo") or "").strip()
        c.estado = EstadoCita.CANCELADA
        c.cancelada_por = request.user
        c.motivo_cancelacion = motivo[:255]
        c.full_clean()
        c.save()

        messages.info(request, "Cita cancelada.")
        return redirect(request.META.get("HTTP_REFERER", "turnos:agenda_dia"))

    return render(request, "turnos/docente/cita_cancelar_confirm.html", {"cita": c})


@requiere_roles("Docente", "DocenteAdministrador")
def calendario_mes(request):
    inst = request.user.institucion

    docente, _ = PerfilDocente.objects.get_or_create(
        usuario=request.user,
        institucion=inst,
        defaults={"minutos_por_bloque": 20, "activo": True},
    )

    hoy = timezone.localdate()
    y = int(request.GET.get("y", hoy.year))
    m = int(request.GET.get("m", hoy.month))

    _, dias_en_mes = monthrange(y, m)
    dias = [date(y, m, d) for d in range(1, dias_en_mes + 1)]

    # ---- Citas del mes SOLO de esta institución ----
    citas = Cita.objects.filter(
        docente=docente,
        institucion=inst,
        inicio__year=y,
        inicio__month=m
    )

    dias_con_citas = {c.inicio.date() for c in citas}

    # ---- Disponibilidad semanal ----
    disp_por_dia = {
        d.dia_semana
        for d in DisponibilidadSemanal.objects.filter(docente=docente, institucion=inst)
    }

    # ---- Bloqueos ----
    bloqueos = ExcepcionDisponibilidad.objects.filter(
        docente=docente,
        institucion=inst,
        fecha__year=y,
        fecha__month=m
    )
    dias_bloqueados = {b.fecha for b in bloqueos}

    calendario = []
    for d in dias:
        estado = "sin_disp"

        if d in dias_bloqueados:
            estado = "bloqueado"
        elif d.weekday() in disp_por_dia:
            estado = "libre"
        if d in dias_con_citas:
            estado = "con_citas"

        calendario.append((d, estado))

    mes_ant = (date(y, m, 1) - timedelta(days=1))
    mes_sig = (date(y, m, dias_en_mes) + timedelta(days=1))

    return render(request, "docente/calendario_mes.html", {
        "calendario": calendario,
        "y": y, "m": m,
        "mes_ant": mes_ant,
        "mes_sig": mes_sig,
    })

@requiere_roles("Docente", "DocenteAdministrador", "Administrador")
def comentar_cita(request, cita_id):
    inst = request.user.institucion

    cita = get_object_or_404(
        Cita,
        pk=cita_id,
        institucion=inst
    )

    # Formulario para NUEVO comentario
    form = NuevoComentarioCitaForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        comentario = form.save(commit=False)
        comentario.cita = cita
        comentario.autor = request.user
        comentario.save()

        messages.success(request, "Comentario agregado al historial.")
        return redirect("comentar_cita", cita_id=cita.id)

    # Historial de comentarios
    comentarios = cita.comentarios.select_related("autor").order_by("creado_en")

    return render(
        request,
        "docente/comentar_cita.html",
        {
            "cita": cita,
            "form": form,
            "comentarios": comentarios,
        }
    )


@requiere_roles("Docente", "DocenteAdministrador", "Administrador")
def editar_comentario_cita(request, comentario_id):
    inst = request.user.institucion

    comentario = get_object_or_404(
        ComentarioCita,
        pk=comentario_id,
        cita__institucion=inst
    )

    # Permisos:
    # - Admin puede editar cualquiera
    # - Otros solo sus propios comentarios
    if request.user.rol.nombre != "Administrador" and comentario.autor != request.user:
        raise PermissionDenied("No puedes editar este comentario.")

    form = NuevoComentarioCitaForm(request.POST or None, instance=comentario)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Comentario actualizado.")
        return redirect("comentar_cita", cita_id=comentario.cita.id)

    return render(
        request,
        "docente/editar_comentario.html",
        {
            "comentario": comentario,
            "form": form,
        }
    )


@requiere_roles("DocenteAdministrador", "Administrador")
def eliminar_comentario_cita(request, comentario_id):
    inst = request.user.institucion

    comentario = get_object_or_404(
        ComentarioCita,
        pk=comentario_id,
        cita__institucion=inst
    )

    if request.method == "POST":
        cita_id = comentario.cita.id
        comentario.delete()
        messages.success(request, "Comentario eliminado.")
        return redirect("comentar_cita", cita_id=cita_id)

    return render(
        request,
        "docente/eliminar_comentario.html",
        {
            "comentario": comentario,
        }
    )
