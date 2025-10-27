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
from .forms_representante import BuscarSemanaForm


TZ = timezone.get_current_timezone()


@requiere_rol("Representante")
@require_http_methods(["GET", "POST"])
def rep_buscar_slots(request):
    # Bind según método (tu form de búsqueda ahora es GET)
    if request.method == "GET":
        form = BuscarSlotsForm(request.GET or None)
    else:
        form = BuscarSlotsForm(request.POST or None)

    slots = []
    docente = None
    fecha = None
    minuto = None

    if form.is_bound and form.is_valid():
        docente = form.cleaned_data["docente"]
        fecha = form.cleaned_data["fecha"]                # date
        minuto = docente.minutos_por_bloque or 20

        starts = generar_slots(docente, fecha)            # list[datetime]
        slots = [(s, s + timezone.timedelta(minutes=minuto)) for s in starts]

        # Opcional: mensaje de diagnóstico si no hay slots
        if not slots:
            messages.info(request,
                "No hay horarios disponibles para ese día. "
                "Posibles causas: sin franjas semanales para ese día, "
                "excepciones de bloqueo, todas las franjas ocupadas, "
                "o si es hoy: los horarios ya pasaron."
            )
    elif form.is_bound and not form.is_valid():
        messages.error(request, "Revisa los datos del formulario.")

    return render(request, "representante/buscar_slots.html", {
        "form": form, "docente": docente, "fecha": fecha, "slots": slots, "minuto": minuto
    })


@requiere_rol("Representante")
@require_POST
def rep_reservar_cita(request):
    form = ReservaCitaForm(request.POST)
    print(form)
    if not form.is_valid():
        messages.error(request, "Por favor completa todos los datos de la cita.")
        # Reconstruir la pantalla de búsqueda con el mismo docente/fecha si podemos
        docente_id = request.POST.get("docente_id")
        docente = get_object_or_404(PerfilDocente, pk=docente_id) if docente_id else None
        fecha_str = request.POST.get("inicio_iso", "")[:10]  # YYYY-MM-DD
        fecha = None
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else None
        except Exception:
            pass

        # Armar los slots de ese día para que el usuario reintente
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
            # Opcional: pasar errores del form de reserva
            "form_reserva_errors": form.errors,
        })

    docente = get_object_or_404(PerfilDocente, pk=form.cleaned_data["docente_id"])
    # parse inicio aware
    ini = datetime.fromisoformat(form.cleaned_data["inicio_iso"])  # naive
    inicio = timezone.make_aware(ini, TZ)

    try:
        reservar_cita(
            docente=docente,
            representante=request.user,
            curso_estudiante=form.cleaned_data["curso_estudiante"],
            nombre_estudiante=form.cleaned_data["nombre_estudiante"],
            motivo=form.cleaned_data["motivo"],
            inicio=inicio,
        )
        messages.success(request, "Cita creada exitosamente. Queda pendiente de confirmación.")
        return redirect("rep_mis_citas")
    except Exception as e:
        messages.error(request, str(e))
        # Mismo fallback de arriba para reintento:
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
        })

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