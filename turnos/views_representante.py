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
    form_reserva = ReservaCitaForm(representante=request.user)

    # Form principal: SOLO docente
    form = BuscarSlotsForm(request.GET or None)

    # Form de filtro
    filtro_form = BuscarDocenteMateriaCursoForm(request.GET or None)
    docentes_filtrados = PerfilDocente.objects.all()

    if filtro_form.is_valid():
        materia = filtro_form.cleaned_data.get("materia")
        curso = filtro_form.cleaned_data.get("curso")

        if materia:
            docentes_filtrados = docentes_filtrados.filter(asignaciones__materia=materia)

        if curso:
            docentes_filtrados = docentes_filtrados.filter(asignaciones__cursos=curso)

        if materia or curso:
            messages.success(request, "Filtro aplicado. Ahora selecciona un docente.")

    # Aplicar filtro al selector de docentes
    try:
        form.fields["docente"].queryset = docentes_filtrados
    except:
        pass

    # Si el formulario principal es válido → ir al calendario
    if form.is_valid() and "docente" in request.GET:
        docente = form.cleaned_data["docente"]
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
    docente_id = request.GET.get("docente_id") or request.POST.get("docente_id")
    inicio_iso = request.GET.get("inicio_iso") or request.POST.get("inicio_iso")

    if not docente_id or not inicio_iso:
        messages.error(request, "Faltan datos para procesar la reserva.")
        return redirect("rep_buscar_slots")

    docente = get_object_or_404(PerfilDocente, pk=docente_id)

    # Convertir inicio_iso → datetime aware
    try:
        ini_naive = datetime.fromisoformat(inicio_iso)
        inicio = timezone.make_aware(ini_naive, TZ)
    except Exception:
        messages.error(request, "Horario inválido.")
        return redirect("rep_buscar_slots")

    # Form de reserva
    form = ReservaCitaForm(request.POST or None, representante=request.user)

    # POST → guardar cita
    if request.method == "POST" and form.is_valid():

        # Extraer datos reales desde la relación
        relacion = form.cleaned_data["estudiante_rel"]
        estudiante = relacion.estudiante
        curso_estudiante = estudiante.curso
        nombre_estudiante = estudiante.nombre

        try:
            reservar_cita(
                docente=docente,
                representante=request.user,
                curso_estudiante=curso_estudiante,
                nombre_estudiante=nombre_estudiante,
                motivo=form.cleaned_data["motivo"],
                inicio=inicio,
            )
            messages.success(request, "Cita creada correctamente.")
            return redirect("rep_mis_citas")
        except Exception as e:
            messages.error(request, str(e))

    # GET → mostrar formulario final
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
    qs = Cita.objects.filter(representante=request.user).order_by("-inicio")
    return render(request, "representante/mis_citas.html", {"citas": qs})

@requiere_rol("Representante")
@require_http_methods(["GET", "POST"])
def rep_cita_cancelar(request, pk):
    cita = get_object_or_404(Cita, pk=pk, representante=request.user)
    if request.method == "POST":
        motivo = (request.POST.get("motivo") or "").strip()
        try:
            cancelar_cita_por_representante(cita=cita, usuario=request.user, motivo=motivo)
            messages.info(request, "Cita cancelada correctamente.")
            enviar_notificacion(
                asunto="Cita cancelada",
                template="emails/cita_cancelada.html",
                contexto={
                    "nombre_receptor": cita.representante.get_full_name() or cita.representante.username,
                    "docente": cita.docente.usuario.get_full_name() or cita.docente.usuario.username,
                    "representante": cita.representante.get_full_name() or cita.representante.username,
                    "inicio": cita.inicio,
                    "motivo_cancelacion": cita.motivo_cancelacion,
                },
                destinatarios=[cita.representante.email, cita.docente.usuario.email] + obtener_emails_admins(),
            )
            return redirect("rep_mis_citas")
        except ValidationError as e:
            messages.error(request, "; ".join(e.messages))
        except Exception as e:
            messages.error(request, str(e))
        return redirect("rep_mis_citas")

    # GET -> confirmar
    return render(request, "representante/cita_cancelar_confirm.html", {"cita": cita})

@requiere_rol("Representante")
@require_http_methods(["GET", "POST"])
def rep_buscar_semana(request):
    form = BuscarSemanaForm(request.POST or None)
    semana = []  # lista de (fecha, slots:list[(inicio, fin)])
    docente = None
    di = None  # lunes
    df = None  # domingo
    minuto = None

    if request.method == "POST" and form.is_valid():
        docente = form.cleaned_data["docente"]
        base = form.cleaned_data["fecha"]
        # Lunes de la semana de 'base'
        di = base - timedelta(days=base.weekday())
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
    "today": timezone.localdate(),  # 👈 para el botón Semana actual
})

from .services import proponer_cita

@requiere_rol("Representante")
@require_POST
def rep_proponer_cita(request):
    docente_id = request.POST.get("docente_id")
    fecha = request.POST.get("fecha")
    hora = request.POST.get("hora")
    motivo = request.POST.get("motivo")

    docente = get_object_or_404(PerfilDocente, pk=docente_id)

    # Construir datetime
    ini = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
    inicio = timezone.make_aware(ini, TZ)

    # Tomar estudiante como ya lo haces
    rel = RelacionRepresentacion.objects.filter(
        representante=request.user, activo=True
    ).first()

    if not rel:
        messages.error(request, "No tienes estudiantes registrados.")
        return redirect("rep_buscar")

    try:
        proponer_cita(
            docente=docente,
            representante=request.user,
            curso_estudiante=rel.estudiante.curso,
            nombre_estudiante=rel.estudiante.nombre,
            motivo=motivo,
            inicio=inicio
        )
        messages.success(request, "Horario propuesto. Queda pendiente de aprobación del docente.")
        return redirect("rep_mis_citas")

    except Exception as e:
        messages.error(request, str(e))
        return redirect("rep_buscar")


@requiere_rol("Representante")
def rep_calendario_docente(request, docente_id):
    docente = get_object_or_404(PerfilDocente, pk=docente_id)

    # Por ahora solo mandamos el docente; luego conectamos slots vía JSON
    return render(
        request,
        "representante/calendario_docente.html",
        {
            "docente": docente,
        },
    )


from datetime import datetime, timedelta, date
from django.http import JsonResponse

@requiere_rol("Representante")
def api_slots_docente(request, docente_id):
    docente = get_object_or_404(PerfilDocente, pk=docente_id)

    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    print("RAW start:", start_str)
    print("RAW end:", end_str)

    if not start_str or not end_str:
        return JsonResponse([], safe=False)

    try:
        # Tomar solo YYYY-MM-DD
        start_date = datetime.strptime(start_str[:10], "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str[:10], "%Y-%m-%d").date()
    except Exception as e:
        print("EXCEPCIÓN:", e)
        return JsonResponse([], safe=False)

    events = []

    current = start_date
    while current <= end_date:

        try:
            slots = generar_slots(docente, current)
        except Exception as e:
            print("Error generando slots:", e)
            slots = []

        if slots:
            events.append({
                "title": "Disponible",
                "start": current.isoformat(),
                "allDay": True,
                "color": "#28a745"
            })

        current += timedelta(days=1)

    return JsonResponse(events, safe=False)


@requiere_rol("Representante")
def rep_slots_dia(request):
    docente_id = request.GET.get("docente")
    fecha_str = request.GET.get("fecha")

    if not docente_id or not fecha_str:
        messages.error(request, "Faltan parámetros para ver los horarios.")
        return redirect("rep_buscar_slots")

    docente = get_object_or_404(PerfilDocente, pk=docente_id)

    # Convertir fecha
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except Exception:
        messages.error(request, "Fecha inválida.")
        return redirect("rep_buscar_slots")

    # Generar slots libres
    minuto = docente.minutos_por_bloque or 20
    starts = generar_slots(docente, fecha)
    slots = [(s, s + timezone.timedelta(minutes=minuto)) for s in starts]

    return render(
        request,
        "representante/slots_dia.html",
        {
            "docente": docente,
            "fecha": fecha,
            "slots": slots,
        },
    )
