# Create your models here.

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from datetime import timedelta

# ---------------------------------
# Utilidades
# ---------------------------------
DIAS_SEMANA = (
    (0, "Lunes"),
    (1, "Martes"),
    (2, "Miércoles"),
    (3, "Jueves"),
    (4, "Viernes"),
    (5, "Sábado"),
    (6, "Domingo"),
)

# ---------------------------------
# Perfiles
# ---------------------------------
class PerfilDocente(models.Model):
    """
    Parámetros de agenda del docente.
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil_docente"
    )
    minutos_por_bloque = models.PositiveIntegerField(default=20)
    maximo_citas_diarias = models.PositiveIntegerField(null=True, blank=True)
    departamento = models.CharField(max_length=120, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Perfil de Docente"
        verbose_name_plural = "Perfiles de Docente"
        ordering = ["usuario__username"]

    def __str__(self):
        return f"Docente: {self.usuario.get_full_name() or self.usuario.username}"


class PerfilRepresentante(models.Model):
    """
    Datos del padre/madre/representante.
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil_representante"
    )
    telefono = models.CharField(max_length=30, blank=True)

    class Meta:
        verbose_name = "Perfil de Representante"
        verbose_name_plural = "Perfiles de Representante"
        ordering = ["usuario__username"]

    def __str__(self):
        return f"Representante: {self.usuario.get_full_name() or self.usuario.username}"

class EstadoCita(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    CONFIRMADA = "CONFIRMADA", "Confirmada"
    CANCELADA = "CANCELADA", "Cancelada"


class Cita(models.Model):
    """
    Cita entre un representante y un docente.
    'inicio' y 'fin' deben alinearse a 'minutos_por_bloque' del docente.
    """
    docente = models.ForeignKey(
        PerfilDocente, on_delete=models.PROTECT, related_name="citas"
    )
    representante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="citas"
    )

    curso_estudiante = models.CharField(max_length=100)   # p.ej. "8vo A", "2do BGU"
    nombre_estudiante = models.CharField(max_length=120)  # nombre del representado
    motivo = models.TextField()

    inicio = models.DateTimeField()
    fin = models.DateTimeField()

    estado = models.CharField(
        max_length=12, choices=EstadoCita.choices, default=EstadoCita.PENDIENTE
    )
    creada_en = models.DateTimeField(auto_now_add=True)

    # Auditoría de cancelación
    cancelada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="citas_canceladas",
    )
    motivo_cancelacion = models.CharField(max_length=255, blank=True)
    estudiante = models.ForeignKey(
        'turnos.Estudiante',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="citas"
    )

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ("docente", "inicio")
        constraints = [
            models.UniqueConstraint(
                fields=["docente", "inicio", "fin"], name="unica_cita_docente_rango"
            ),
            models.CheckConstraint(
                check=models.Q(fin__gt=models.F("inicio")), name="cita_fin_gt_inicio"
            ),
        ]
        indexes = [
            models.Index(fields=["docente", "inicio"]),
            models.Index(fields=["estado"]),
            models.Index(fields=["inicio"]),
        ]

    def __str__(self):
        return f"{self.inicio:%Y-%m-%d %H:%M} - {self.docente} con {self.nombre_estudiante}"

    def clean(self):
        # No permitir pasado (a menos que tengas un flujo de carga histórica)
        if self.inicio and self.inicio < timezone.now():
            raise ValidationError("No se permiten citas en el pasado.")

        if self.fin and self.inicio and self.fin <= self.inicio:
            raise ValidationError("La hora fin debe ser mayor que la hora inicio.")

        # Respetar máximo diario del docente (si está definido)
        if self.docente and self.inicio:
            if self.docente.maximo_citas_diarias:
                tz = timezone.get_current_timezone()
                fecha_local = timezone.localtime(self.inicio, tz).date()
                conteo = (
                    Cita.objects.filter(
                        docente=self.docente,
                        inicio__date=fecha_local,
                        estado__in=[EstadoCita.PENDIENTE, EstadoCita.CONFIRMADA],
                    )
                    .exclude(pk=self.pk)
                    .count()
                )
                if conteo >= self.docente.maximo_citas_diarias:
                    raise ValidationError("El docente alcanzó el máximo de citas para ese día.")

        # 2.a) Antelación mínima 24h
        if self.inicio and self.inicio < timezone.now() + timedelta(hours=24):
            raise ValidationError("Debes reservar con al menos 24 horas de antelación.")

        # 2.b) Alineación a bloques del docente
        if self.docente and self.inicio and self.fin:
            tam = self.docente.minutos_por_bloque
            dur = int((self.fin - self.inicio).total_seconds() // 60)
            if dur != tam:
                raise ValidationError(f"La duración de la cita debe ser exactamente {tam} minutos.")
            # inicio alineado: minutos y segundos relativos a 00:00 deben ser múltiplo de tam
            minutos_desde_medianoche = self.inicio.hour * 60 + self.inicio.minute
            if minutos_desde_medianoche % tam != 0 or self.inicio.second != 0:
                raise ValidationError("La hora de inicio debe coincidir con el tamaño del bloque del docente.")

        # 2.c) Solape con otras citas del mismo docente
        if self.docente and self.inicio and self.fin:
            solapa = Cita.objects.filter(
                docente=self.docente,
                estado__in=[EstadoCita.PENDIENTE, EstadoCita.CONFIRMADA],
                inicio__lt=self.fin,
                fin__gt=self.inicio,
            ).exclude(pk=self.pk).exists()
            if solapa:
                raise ValidationError("El docente ya tiene una cita en ese rango de tiempo.")
            
    @property
    def duracion_minutos(self) -> int:
        return int((self.fin - self.inicio).total_seconds() // 60)

class DisponibilidadSemanal(models.Model):
    docente = models.ForeignKey("turnos.PerfilDocente", on_delete=models.CASCADE, related_name="disponibilidades")
    dia_semana = models.IntegerField(choices=[(i, n) for i, n in enumerate(["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"])])
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        verbose_name = "Disponibilidad semanal"
        verbose_name_plural = "Disponibilidades semanales"
        unique_together = [("docente", "dia_semana", "hora_inicio", "hora_fin")]
        indexes = [models.Index(fields=["docente","dia_semana"])]

    def clean(self):
        if self.hora_fin <= self.hora_inicio:
            raise ValidationError("La hora fin debe ser mayor que la hora inicio.")

    def __str__(self):
        return f"{self.get_dia_semana_display()} {self.hora_inicio}-{self.hora_fin} / {self.docente}"
    

class TipoExcepcion(models.TextChoices):
    BLOQUEO = "BLOQUEO", "Bloqueo"
    EXTRA = "EXTRA", "Extra"

class ExcepcionDisponibilidad(models.Model):
    docente = models.ForeignKey("turnos.PerfilDocente", on_delete=models.CASCADE, related_name="excepciones")
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    tipo = models.CharField(max_length=10, choices=TipoExcepcion.choices, default=TipoExcepcion.BLOQUEO)
    motivo = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Excepción de disponibilidad"
        verbose_name_plural = "Excepciones de disponibilidad"
        indexes = [models.Index(fields=["docente","fecha"])]

    def clean(self):
        if self.hora_fin <= self.hora_inicio:
            raise ValidationError("La hora fin debe ser mayor que la hora inicio.")

    def __str__(self):
        return f"{self.fecha} {self.hora_inicio}-{self.hora_fin} ({self.tipo}) / {self.docente}"
    

# --- Estudiantes y relación con representantes ---

from django.core.validators import RegexValidator

class Estudiante(models.Model):
    nombre = models.CharField(max_length=120)
    cedula = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r"^\d{8,20}$", "Cédula inválida (solo dígitos, 8-20).")]
    )
    curso = models.CharField(max_length=80)  # p.ej. "8vo A", "2do BGU"

    # Opcional: activo para bajas temporales
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"
        ordering = ["curso", "nombre"]
        indexes = [
            models.Index(fields=["curso"]),
            models.Index(fields=["activo"]),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.curso})"

class FuenteRelacion(models.TextChoices):
    MANUAL = "MANUAL", "Manual"
    IMPORT = "IMPORT", "Importación"

class RelacionRepresentacion(models.Model):
    """
    Relación muchos-a-muchos entre Representante (User) y Estudiante, con metadata.
    """
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name="relaciones")
    representante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="relaciones_representacion"
    )
    parentesco = models.CharField(max_length=40, blank=True)  # p.ej. Madre, Padre, Tía/o
    verificado = models.BooleanField(default=False)
    fuente = models.CharField(max_length=10, choices=FuenteRelacion.choices, default=FuenteRelacion.MANUAL)
    activo = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Relación Representación"
        verbose_name_plural = "Relaciones de Representación"
        # Evitar duplicados activos para la misma pareja
        constraints = [
            models.UniqueConstraint(
                fields=["estudiante", "representante"],
                name="unica_relacion_estudiante_representante"
            )
        ]
        indexes = [
            models.Index(fields=["representante"]),
            models.Index(fields=["estudiante"]),
            models.Index(fields=["activo"]),
            models.Index(fields=["verificado"]),
        ]

    def __str__(self):
        estado = "✓" if self.verificado else "•"
        return f"{estado} {self.representante.email} ↔ {self.estudiante}"

class FeriadoInstitucional(models.Model):
    nombre = models.CharField(max_length=120)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    hora_inicio = models.TimeField(null=True, blank=True)  # si null => día completo
    hora_fin = models.TimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Feriado/Evento institucional"
        verbose_name_plural = "Feriados/Eventos institucionales"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        if self.hora_inicio and self.hora_fin:
            return f"{self.nombre} ({self.fecha_inicio}–{self.fecha_fin} {self.hora_inicio}-{self.hora_fin})"
        return f"{self.nombre} ({self.fecha_inicio}–{self.fecha_fin} - día completo)"
