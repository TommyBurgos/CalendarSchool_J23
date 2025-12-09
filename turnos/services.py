# turnos/services.py
from django.db import transaction
from django.utils import timezone
from datetime import timedelta, datetime, time
from typing import List, Tuple
from .models import DisponibilidadSemanal, ExcepcionDisponibilidad, Cita, EstadoCita, PerfilDocente, TipoExcepcion, ValidationError
from .emailing import enviar_notificacion, obtener_emails_admins



def _esta_en_disponibilidad(docente, inicio_dt, fin_dt):
    # 1) Excepciones
    fecha = inicio_dt.date()
    t_ini, t_fin = inicio_dt.time(), fin_dt.time()

    exc_bloqueo = docente.excepciones.filter(
        fecha=fecha,
        hora_inicio__lt=t_fin,
        hora_fin__gt=t_ini,
        tipo="BLOQUEO"
    ).exists()
    if exc_bloqueo:
        return False

    exc_extra = docente.excepciones.filter(
        fecha=fecha,
        hora_inicio__lte=t_ini,
        hora_fin__gte=t_fin,
        tipo="EXTRA"
    ).exists()
    if exc_extra:
        return True

    # 2) Disponibilidad semanal
    dia = inicio_dt.weekday()
    return docente.disponibilidades.filter(
        dia_semana=dia,
        hora_inicio__lte=t_ini,
        hora_fin__gte=t_fin
    ).exists()


@transaction.atomic
def reservar_cita(docente, representante, curso_estudiante, nombre_estudiante, motivo, inicio, minutos_bloque=20):

    inst = docente.institucion   # 🔥 MULTITENANT

    fin = inicio + timedelta(minutes=minutos_bloque)

    if inicio < timezone.now() + timedelta(hours=24):
        raise ValidationError("Debes reservar con al menos 24 horas de antelación.")

    if not _esta_en_disponibilidad(docente, inicio, fin):
        raise ValidationError("El docente no está disponible en ese horario.")

    # -------- LIMITES POR REPRESENTANTE --------
    fecha = timezone.localtime(inicio).date()
    from .models import Cita, EstadoCita

    diarias = Cita.objects.filter(
        representante=representante,
        institucion=inst,           # 🔥 MULTITENANT
        inicio__date=fecha,
        estado__in=[EstadoCita.PENDIENTE, EstadoCita.CONFIRMADA]
    ).count()

    if diarias >= 1:
        raise ValidationError("Máximo 1 cita por día.")

    semana_ini = fecha - timedelta(days=fecha.weekday())
    semana_fin = semana_ini + timedelta(days=6)

    semanales = Cita.objects.filter(
        representante=representante,
        institucion=inst,            # 🔥 MULTITENANT
        inicio__date__range=(semana_ini, semana_fin),
        estado__in=[EstadoCita.PENDIENTE, EstadoCita.CONFIRMADA]
    ).count()

    if semanales >= 2:
        raise ValidationError("Máximo 2 citas por semana.")

    # -------- CREAR CITA --------
    cita = Cita(
        docente=docente,
        representante=representante,
        institucion=inst,              # 🔥 MUY IMPORTANTE
        curso_estudiante=curso_estudiante,
        nombre_estudiante=nombre_estudiante,
        motivo=motivo,
        inicio=inicio,
        fin=fin,
        estado=EstadoCita.PENDIENTE,
    )

    cita.full_clean()
    cita.save()
    return cita


# -------- utilidades de intervalos (aware) --------
Intervalo = Tuple[datetime, datetime]

def _merge(intervalos: List[Intervalo]) -> List[Intervalo]:
    if not intervalos: return []
    xs = sorted(intervalos, key=lambda x: x[0])
    res = [xs[0]]
    for s,e in xs[1:]:
        ls, le = res[-1]
        if s <= le:
            res[-1] = (ls, max(le, e))
        else:
            res.append((s,e))
    return res

def _subtract(a: List[Intervalo], b: List[Intervalo]) -> List[Intervalo]:
    """ Resta B a A (A-B). Todos conscientes de tz. """
    res = []
    for s,e in a:
        cur_start = s
        for bs,be in b:
            if be <= cur_start or bs >= e:
                continue
            if bs > cur_start:
                res.append((cur_start, bs))
            cur_start = max(cur_start, be)
            if cur_start >= e:
                break
        if cur_start < e:
            res.append((cur_start, e))
    return res

def _split_en_bloques(intervalos: List[Intervalo], minutos: int) -> List[datetime]:
    starts = []
    for s,e in intervalos:
        t = s
        while t + timedelta(minutes=minutos) <= e:
            starts.append(t)
            t += timedelta(minutes=minutos)
    return starts

# -------- core slots --------
def generar_slots(docente: PerfilDocente, fecha) -> List[datetime]:
    # ✅ Guardia defensiva: si no hay fecha, no cruja
    if not fecha:
        return []
    """
    Devuelve lista de datetimes (aware) con inicio de cada slot libre
    para 'docente' en la 'fecha' dada (date o str YYYY-MM-DD).
    Reglas:
      - Parte de DisponibilidadSemanal del día.
      - Aplica EXTRAS (suman) y BLOQUEOS (restan).
      - Quita Citas PENDIENTE/CONFIRMADA.
      - Respeta tamaño de bloque docente.
      - Filtra pasado y regla de 24h (MVP: se aplica).
    """
    tz = timezone.get_current_timezone()
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, "%Y-%m-%d").date()

    # 1) base de disponibilidad semanal del día
    dia = fecha.weekday()  # 0=Lunes
    bases: List[Intervalo] = []
    for d in DisponibilidadSemanal.objects.filter(docente=docente, dia_semana=dia).order_by("hora_inicio"):
        s = timezone.make_aware(datetime.combine(fecha, d.hora_inicio), tz)
        e = timezone.make_aware(datetime.combine(fecha, d.hora_fin), tz)
        if e > s:
            bases.append((s,e))
    bases = _merge(bases)

    # 2) aplicar EXTRAS (sumar)
    extras: List[Intervalo] = []
    for ex in ExcepcionDisponibilidad.objects.filter(docente=docente, fecha=fecha, tipo=TipoExcepcion.EXTRA):
        s = timezone.make_aware(datetime.combine(fecha, ex.hora_inicio), tz)
        e = timezone.make_aware(datetime.combine(fecha, ex.hora_fin), tz)
        if e > s:
            extras.append((s,e))
    union = _merge(bases + extras)

    # 3) aplicar BLOQUEOS (restar)
    bloqueos: List[Intervalo] = []
    for bl in ExcepcionDisponibilidad.objects.filter(docente=docente, fecha=fecha, tipo=TipoExcepcion.BLOQUEO):
        s = timezone.make_aware(datetime.combine(fecha, bl.hora_inicio), tz)
        e = timezone.make_aware(datetime.combine(fecha, bl.hora_fin), tz)
        if e > s:
            bloqueos.append((s,e))
    disponible = _subtract(union, _merge(bloqueos))

    # 4) quitar citas existentes
    citas_intervals: List[Intervalo] = []
    for c in Cita.objects.filter(
        docente=docente,
        estado__in=[EstadoCita.PENDIENTE, EstadoCita.CONFIRMADA],
        inicio__date=fecha,
    ).only("inicio","fin"):
        citas_intervals.append((c.inicio, c.fin))
    disponible = _subtract(disponible, _merge(citas_intervals))

    # 5) partir en bloques del docente
    minutos = docente.minutos_por_bloque or 20
    # Alinear al tamaño de bloque (redondeo hacia arriba del inicio)
    alineados = []
    for s,e in disponible:
        # redondear s al siguiente múltiplo
        mins_mid = s.hour*60 + s.minute
        resto = mins_mid % minutos
        if resto != 0 or s.second or s.microsecond:
            delta = minutos - resto if resto != 0 else 0
            s = s.replace(second=0, microsecond=0) + timedelta(minutes=delta)
        if s < e:
            alineados.append((s,e))
    disponible = alineados

    starts = _split_en_bloques(disponible, minutos)

    # 6) filtrar pasado y regla de 24h (MVP)
    ahora = timezone.localtime(timezone.now(), tz)
    min_inicio = ahora + timedelta(hours=24)
    starts = [dt for dt in starts if dt >= min_inicio]

    return starts

def _uniq_emails(emails: List[str]) -> List[str]:
    """Quita None/'' y duplicados preservando orden."""
    seen = set()
    out = []
    for e in emails or []:
        if e and e not in seen:
            seen.add(e)
            out.append(e)
    return out


@transaction.atomic
def reservar_cita(
    *,
    docente: PerfilDocente,
    representante,
    curso_estudiante: str,
    nombre_estudiante: str,
    motivo: str,
    inicio: datetime,
    minutos_bloque: int = None,
) -> Cita:

    inst = representante.institucion  # ← INSTITUCIÓN AQUÍ

    # Normalizar fecha
    inicio = (
        timezone.make_aware(inicio.replace(second=0, microsecond=0), timezone.get_current_timezone())
        if timezone.is_naive(inicio) else inicio
    )

    # Validación 24h
    if inicio < timezone.now() + timedelta(hours=24):
        raise ValidationError("Debes reservar con al menos 24 horas de antelación.")

    minuto = minutos_bloque or (docente.minutos_por_bloque or 20)
    fin = inicio + timedelta(minutes=minuto)

    # Validar slot existente
    fecha = timezone.localtime(inicio).date()
    starts = generar_slots(docente, fecha)
    if inicio not in starts:
        raise ValidationError("El horario seleccionado ya no está disponible.")

    # Límites del representante
    semana_ini = fecha - timedelta(days=fecha.weekday())
    semana_fin = semana_ini + timedelta(days=6)
    q = Cita.objects.filter(
        representante=representante,
        institucion=inst,
        estado__in=[EstadoCita.PENDIENTE, EstadoCita.CONFIRMADA]
    )
    if q.filter(inicio__date=fecha).count() >= 1:
        raise ValidationError("Máximo 1 cita por día.")
    if q.filter(inicio__date__range=(semana_ini, semana_fin)).count() >= 2:
        raise ValidationError("Máximo 2 citas por semana.")

    # Crear cita con institución
    cita = Cita(
        docente=docente,
        representante=representante,
        institucion=inst,
        curso_estudiante=curso_estudiante,
        nombre_estudiante=nombre_estudiante,
        motivo=motivo,
        inicio=inicio,
        fin=fin,
        estado=EstadoCita.CONFIRMADA,
    )
    cita.full_clean()
    cita.save()

    # Notificación
    enviar_notificacion(
        asunto="Nueva cita registrada",
        template="emails/cita_creada.html",
        contexto={
            "docente": cita.docente.usuario.get_full_name() or cita.docente.usuario.username,
            "representante": cita.representante.get_full_name() or cita.representante.username,
            "inicio": cita.inicio,
            "motivo": cita.motivo,
            "estado": cita.get_estado_display(),
            "nombre_receptor": "Usuario",
        },
        destinatarios=_uniq_emails([
            cita.docente.usuario.email,
            cita.representante.email,
            *obtener_emails_admins(),
        ]),
    )

    return cita

@transaction.atomic
def cancelar_cita_por_representante(*, cita: Cita, usuario, motivo: str = "") -> Cita:
    """
    Cancela una cita por el Representante:
      - Solo si es el dueño
      - Solo si está PENDIENTE o CONFIRMADA
      - Requiere antelación ≥ 24h
    Envía notificación a Docente + Representante + Admins.
    """
    inst = usuario.institucion

    # Seguridad multi-institución
    if cita.institucion_id != inst.id:
        raise ValidationError("No puedes modificar citas de otra institución.")

    if cita.representante_id != usuario.id:
        raise ValidationError("No puede cancelar citas de otra persona.")

    if cita.estado not in [EstadoCita.PENDIENTE, EstadoCita.CONFIRMADA]:
        raise ValidationError("Esta cita no puede cancelarse.")

    if timezone.now() > (cita.inicio - timedelta(hours=24)):
        raise ValidationError("Las cancelaciones requieren al menos 24 horas de antelación.")

    cita.estado = EstadoCita.CANCELADA
    cita.cancelada_por = usuario
    cita.motivo_cancelacion = (motivo or "")[:255]
    cita.full_clean()
    cita.save()

    destinatarios = _uniq_emails([
        cita.docente.usuario.email,
        cita.representante.email,
        *obtener_emails_admins()  # ← admins de la institución
    ])

    enviar_notificacion(
        asunto="Cita cancelada por el representante",
        template="emails/cita_cancelada.html",
        contexto={
            "docente": cita.docente.usuario.get_full_name() or cita.docente.usuario.username,
            "representante": cita.representante.get_full_name() or cita.representante.username,
            "inicio": cita.inicio,
            "motivo_cancelacion": cita.motivo_cancelacion,
            "nombre_receptor": "Usuario",
        },
        destinatarios=destinatarios,
    )

    return cita

@transaction.atomic
def cancelar_cita_por_docente(*, cita: Cita, usuario_docente, motivo: str = "") -> Cita:
    """
    Cancela una cita por el Docente.
    Valida pertenencia del docente y estado de la cita.
    Envía notificación a Docente + Representante + Admins.
    """
    inst = usuario_docente.institucion

    if cita.institucion_id != inst.id:
        raise ValidationError("No puedes modificar citas de otra institución.")

    perfil_doc = getattr(usuario_docente, "perfil_docente", None)
    if not perfil_doc or perfil_doc.pk != cita.docente_id:
        raise ValidationError("No puede cancelar citas de otro docente.")

    if cita.estado not in [EstadoCita.PENDIENTE, EstadoCita.CONFIRMADA]:
        raise ValidationError("Esta cita no puede cancelarse.")

    cita.estado = EstadoCita.CANCELADA
    cita.cancelada_por = usuario_docente
    cita.motivo_cancelacion = (motivo or "")[:255]
    cita.full_clean()
    cita.save()

    destinatarios = _uniq_emails([
        cita.representante.email,
        cita.docente.usuario.email,
        *obtener_emails_admins()
    ])

    enviar_notificacion(
        asunto="Cita cancelada por el docente",
        template="emails/cita_cancelada.html",
        contexto={
            "docente": cita.docente.usuario.get_full_name() or cita.docente.usuario.username,
            "representante": cita.representante.get_full_name() or cita.representante.username,
            "inicio": cita.inicio,
            "motivo_cancelacion": cita.motivo_cancelacion,
            "nombre_receptor": "Usuario",
        },
        destinatarios=destinatarios,
    )

    return cita

def proponer_cita(*, docente, representante, curso_estudiante, nombre_estudiante, motivo, inicio):
    inst = representante.institucion

    # Evitar solapamientos dentro de la misma institución
    if Cita.objects.filter(docente=docente, institucion=inst, inicio=inicio).exists():
        raise Exception("El docente ya tiene una cita en ese horario.")

    minutos = docente.minutos_por_bloque or 20
    fin = inicio + timedelta(minutes=minutos)

    return Cita.objects.create(
        docente=docente,
        representante=representante,
        institucion=inst,
        curso_estudiante=curso_estudiante,
        nombre_estudiante=nombre_estudiante,
        motivo=motivo,
        inicio=inicio,
        fin=fin,
        estado="PROPUESTA",
    )
