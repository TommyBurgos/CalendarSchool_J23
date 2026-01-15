# turnos/views_representante.py
from datetime import datetime
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST


from user.decorators import requiere_rol
from .models import PerfilDocente, Cita, EstadoCita
from .forms_representante import BuscarSlotsForm, ReservaCitaForm
from .services import generar_slots, reservar_cita

from django.core.exceptions import ValidationError
from .services import cancelar_cita_por_representante
from .emailing import enviar_notificacion, obtener_emails_admins

from datetime import timedelta
from .forms_representante import BuscarSemanaForm, RelacionRepresentacion, BuscarSlotsForm, BuscarDocenteMateriaCursoForm

from django.http import JsonResponse
from django.utils.timezone import make_aware


TZ = timezone.get_current_timezone()


@requiere_rol("Representante")
@require_http_methods(["GET", "POST"])
def rep_buscar_slots(request):
    inst = request.user.institucion

    form_reserva = ReservaCitaForm(representante=request.user)

    # formulario principal
    form = BuscarSlotsForm(request.GET or None)
    
    # filtro por materia/curso
    filtro_form = BuscarDocenteMateriaCursoForm(request.GET or None)

    # Docentes SOLO de la institución
    docentes_filtrados = PerfilDocente.objects.filter(institucion=inst)

    # Aplicar filtros
    if filtro_form.is_valid():
        materia = filtro_form.cleaned_data.get("materia")
        curso = filtro_form.cleaned_data.get("curso")

        if materia:
            docentes_filtrados = docentes_filtrados.filter(
                asignaciones__materia=materia,
                asignaciones__institucion=inst
            )

        if curso:
            docentes_filtrados = docentes_filtrados.filter(
                asignaciones__cursos=curso,
                asignaciones__institucion=inst
            )

        if materia or curso:
            messages.success(request, "Filtro aplicado. Ahora selecciona un docente.")

    # Aplicar filtro al selector
    try:
        form.fields["docente"].queryset = docentes_filtrados
    except:
        pass

    # Si selecciona docente → ir al calendario
    if form.is_valid() and "docente" in request.GET:
        docente = form.cleaned_data["docente"]

        # Seguridad: el docente debe ser de la institución
        if docente.institucion != inst:
            messages.error(request, "Docente inválido.")
            return redirect("rep_buscar_slots")

        return redirect(f"/turnos/representante/calendario/{docente.id}/")

    return render(
        request,
        "representante/buscar_slots.html",
        {
            "form": form,
            "filtro_form": filtro_form,
            "docentes_filtrados": docentes_filtrados,
            "form_reserva": form_reserva,
        }
    )


"""
@requiere_rol("Representante")
@require_POST
def rep_reservar_cita(request):
    form_reserva = ReservaCitaForm(representante=request.user)

    # El form ahora requiere el parámetro representante
    form = ReservaCitaForm(request.POST, representante=request.user)
    print(form)

    if not form.is_valid():
        messages.error(request, "Por favor completa todos los datos de la cita.")

        # Reconstruir pantalla de búsqueda
        docente_id = request.POST.get("docente_id")
        docente = get_object_or_404(PerfilDocente, pk=docente_id) if docente_id else None

        fecha_str = request.POST.get("inicio_iso", "")[:10]  # YYYY-MM-DD
        fecha = None
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else None
        except Exception:
            pass

        slots = []
        minuto = None
        if docente and fecha:
            minuto = docente.minutos_por_bloque or 20
            starts = generar_slots(docente, fecha)
            slots = [(s, s + timezone.timedelta(minutes=minuto)) for s in starts]

        buscar_form = BuscarSlotsForm(initial={"docente": docente, "fecha": fecha})
        return render(request, "representante/buscar_slots.html", {
            "form": buscar_form,
            "docente": docente,
            "fecha": fecha,
            "slots": slots,
            "minuto": minuto,
            "form_reserva": form_reserva,
            "form_reserva_errors": form.errors,
        })

    # Form válido → procesar reserva
    docente = get_object_or_404(PerfilDocente, pk=form.cleaned_data["docente_id"])

    ini = datetime.fromisoformat(form.cleaned_data["inicio_iso"])  # naive
    inicio = timezone.make_aware(ini, TZ)

    # Obtener relación seleccionada
    rel = form.cleaned_data["estudiante_rel"]
    curso_est = rel.estudiante.curso
    nombre_est = rel.estudiante.nombre

    try:
        reservar_cita(
            docente=docente,
            representante=request.user,
            curso_estudiante=curso_est,
            nombre_estudiante=nombre_est,
            motivo=form.cleaned_data["motivo"],
            inicio=inicio,
        )
        messages.success(request, "Cita creada y confirmada exitosamente.")
        return redirect("rep_mis_citas")

    except Exception as e:
        messages.error(request, str(e))

        # Fallback para reintento
        fecha = inicio.date()
        minuto = docente.minutos_por_bloque or 20
        starts = generar_slots(docente, fecha)
        slots = [(s, s + timezone.timedelta(minutes=minuto)) for s in starts]

        buscar_form = BuscarSlotsForm(initial={"docente": docente, "fecha": fecha})
        return render(request, "representante/buscar_slots.html", {
            "form": buscar_form,
            "docente": docente,
            "fecha": fecha,
            "slots": slots,
            "minuto": minuto,
            "form_reserva": form_reserva,
        })
"""
@requiere_rol("Representante")
@require_http_methods(["GET", "POST"])
def rep_reservar(request):
    inst = request.user.institucion

    docente_id = request.GET.get("docente_id") or request.POST.get("docente_id")
    inicio_iso = request.GET.get("inicio_iso") or request.POST.get("inicio_iso")

    if not docente_id or not inicio_iso:
        messages.error(request, "Faltan datos para procesar la reserva.")
        return redirect("rep_buscar_slots")

    docente = get_object_or_404(PerfilDocente, pk=docente_id, institucion=inst)

    # Parsear fecha inicio
    try:
        ini_naive = datetime.fromisoformat(inicio_iso)
        inicio = timezone.make_aware(ini_naive, TZ)
    except Exception:
        messages.error(request, "Horario inválido.")
        return redirect("rep_buscar_slots")

    # Form de reserva
    form = ReservaCitaForm(request.POST or None, representante=request.user)

    if request.method == "POST" and form.is_valid():

        relacion = form.cleaned_data["estudiante_rel"]
        estudiante = relacion.estudiante

        try:
            reservar_cita(
                docente=docente,
                representante=request.user,
                curso_estudiante=estudiante.curso,
                nombre_estudiante=estudiante.nombre,
                motivo=form.cleaned_data["motivo"],
                inicio=inicio,
                #institucion=inst,         # ← MULTITENANT
            )
            messages.success(request, "Cita creada correctamente.")
            return redirect("rep_mis_citas")

        except Exception as e:
            messages.error(request, str(e))

    return render(
        request,
        "representante/reservar.html",
        {
            "docente": docente,
            "inicio": inicio,
            "form": form,
        }
    )


@requiere_rol("Representante")
def rep_mis_citas(request):
    inst = request.user.institucion
    qs = Cita.objects.filter(
        representante=request.user,
        institucion=inst
    ).order_by("-inicio")
    return render(request, "representante/mis_citas.html", {"citas": qs})

@requiere_rol("Representante")
@require_http_methods(["GET", "POST"])
def rep_cita_cancelar(request, pk):
    inst = request.user.institucion

    cita = get_object_or_404(
        Cita,
        pk=pk,
        representante=request.user,
        institucion=inst
    )

    if request.method == "POST":
        motivo = (request.POST.get("motivo") or "").strip()

        try:
            cancelar_cita_por_representante(cita=cita, usuario=request.user, motivo=motivo)
            messages.info(request, "Cita cancelada correctamente.")
            enviar_notificacion(
                asunto="Cita cancelada",
                template="emails/cita_cancelada.html",
                contexto={ ... },
                destinatarios=[ ... ],
            )
            return redirect("rep_mis_citas")

        except Exception as e:
            messages.error(request, str(e))
            return redirect("rep_mis_citas")

    return render(request, "representante/cita_cancelar_confirm.html", {"cita": cita})

#PROBABLEMENTE LA DEJE OBSOLETA POR EL CAMBIO CON EL CALENDARIO
@requiere_rol("Representante")
@require_http_methods(["GET", "POST"])
def rep_buscar_semana(request):
    inst = request.user.institucion

    form = BuscarSemanaForm(request.POST or None)
    semana = []
    docente = None
    di = None
    df = None
    minuto = None

    if request.method == "POST" and form.is_valid():
        docente = form.cleaned_data["docente"]

        # Seguridad multitenant
        if docente.institucion != inst:
            messages.error(request, "Docente no pertenece a tu institución.")
            return redirect("rep_buscar_slots")

        base = form.cleaned_data["fecha"]

        di = base - timedelta(days=base.weekday())  # lunes
        df = di + timedelta(days=6)
        minuto = docente.minutos_por_bloque or 20

        for i in range(7):
            dia = di + timedelta(days=i)
            starts = generar_slots(docente, dia)
            slots = [(s, s + timezone.timedelta(minutes=minuto)) for s in starts]
            semana.append((dia, slots))

    return render(request, "representante/buscar_semana.html", {
        "form": form,
        "docente": docente,
        "di": di,
        "df": df,
        "semana": semana,
        "minuto": minuto,
        "today": timezone.localdate(),
    })

from .services import proponer_cita

@requiere_rol("Representante")
@require_POST
def rep_proponer_cita(request):
    inst = request.user.institucion

    docente_id = request.POST.get("docente_id")
    fecha = request.POST.get("fecha")
    hora = request.POST.get("hora")
    motivo = (request.POST.get("motivo") or "").strip()
    relacion_id = request.POST.get("estudiante_rel")

    if not (docente_id and fecha and hora and relacion_id and motivo):
        messages.error(request, "Completa todos los datos para proponer el horario.")
        return redirect(f"/turnos/representante/slots-dia/?docente={docente_id}&fecha={fecha}")

    docente = get_object_or_404(PerfilDocente, pk=docente_id, institucion=inst)

    relacion = get_object_or_404(
        RelacionRepresentacion,
        pk=relacion_id,
        representante=request.user,
        activo=True,
        institucion=inst
    )

    estudiante = relacion.estudiante

    # fecha + hora → datetime
    try:
        dt_str = f"{fecha} {hora}"
        ini_naive = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        inicio = timezone.make_aware(ini_naive, TZ)
    except Exception:
        messages.error(request, "Fecha u hora inválida.")
        return redirect(f"/turnos/representante/slots-dia/?docente={docente_id}&fecha={fecha}")

    try:
        proponer_cita(
            docente=docente,
            representante=request.user,
            curso_estudiante=getattr(estudiante, "curso", ""),
            nombre_estudiante=getattr(estudiante, "nombre", estudiante.__str__()),
            motivo=motivo,
            inicio=inicio,
            institucion=inst,  # ← AGREGADO
        )

        messages.success(request, "Horario propuesto. Pendiente de aprobación.")
        return redirect("rep_mis_citas")

    except Exception as e:
        messages.error(request, str(e))
        return redirect(f"/turnos/representante/slots-dia/?docente={docente_id}&fecha={fecha}")


@requiere_rol("Representante")
def rep_calendario_docente(request, docente_id):
    inst = request.user.institucion
    docente = get_object_or_404(PerfilDocente, pk=docente_id, institucion=inst)

    return render(
        request,
        "representante/calendario_docente.html",
        {"docente": docente},
    )


from datetime import datetime, timedelta, date
from django.http import JsonResponse

@requiere_rol("Representante")
def api_slots_docente(request, docente_id):
    inst = request.user.institucion
    docente = get_object_or_404(PerfilDocente, pk=docente_id, institucion=inst)

    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    if not start_str or not end_str:
        return JsonResponse([], safe=False)

    try:
        start_date = datetime.strptime(start_str[:10], "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str[:10], "%Y-%m-%d").date()
    except Exception:
        return JsonResponse([], safe=False)

    events = []

    current = start_date
    while current <= end_date:
        try:
            slots = generar_slots(docente, current)
        except Exception:
            slots = []

        if slots:
            events.append({
                "title": "Disponible",
                "start": current.isoformat(),
                "allDay": True,
                "color": "#28a745",
            })

        current += timedelta(days=1)

    return JsonResponse(events, safe=False)


@requiere_rol("Representante")
def rep_slots_dia(request):
    inst = request.user.institucion

    docente_id = request.GET.get("docente")
    fecha_str = request.GET.get("fecha")

    if not docente_id or not fecha_str:
        messages.error(request, "Faltan parámetros para ver los horarios.")
        return redirect("rep_buscar_slots")

    docente = get_object_or_404(PerfilDocente, pk=docente_id, institucion=inst)

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except Exception:
        messages.error(request, "Fecha inválida.")
        return redirect("rep_buscar_slots")

    minuto = docente.minutos_por_bloque or 20
    starts = generar_slots(docente, fecha)
    slots = [(s, s + timezone.timedelta(minutes=minuto)) for s in starts]

    # ✅ RELACIONES del representante (NO estudiantes directos)
    relaciones = RelacionRepresentacion.objects.filter(
        representante=request.user,
        institucion=inst,
        activo=True,
        verificado=True,   # 👈 MUY IMPORTANTE
    ).select_related("estudiante")
    print(f"representante> {request.user}")
    print(f"representante> {inst}")
    print(f"RELACIONES: {relaciones}")
    return render(
        request,
        "representante/slots_dia.html",
        {
            "docente": docente,
            "fecha": fecha,
            "slots": slots,
            "estudiantes": relaciones,  # 👈 el template espera RELACIONES
        },
    )
