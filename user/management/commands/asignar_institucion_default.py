from django.core.management.base import BaseCommand
from django.db import transaction
from user.models import User, Institucion
from turnos.models import PerfilDocente, PerfilRepresentante, Cita, Estudiante

class Command(BaseCommand):
    help = "Asigna una institución por defecto a todos los registros antiguos sin institución."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Iniciando asignación de institución por defecto..."))

        with transaction.atomic():
            inst, _ = Institucion.objects.get_or_create(
                nombre="UNIDAD EDUCATIVA JUAN XXIII",
                defaults={"codigo": "09h00353", "activo": True},
            )

            # Usuarios
            users_actualizados = User.objects.filter(institucion__isnull=True).update(institucion=inst)

            # Perfiles
            docentes_actualizados = PerfilDocente.objects.filter(institucion__isnull=True).update(institucion=inst)
            reps_actualizados = PerfilRepresentante.objects.filter(institucion__isnull=True).update(institucion=inst)

            try:
                estudiantes_actualizados = Estudiante.objects.filter(institucion__isnull=True).update(institucion=inst)
            except Exception:
                estudiantes_actualizados = 0

            # Citas
            citas_actualizadas = Cita.objects.filter(institucion__isnull=True).update(institucion=inst)

        self.stdout.write(self.style.SUCCESS("✔ Proceso completado"))
        self.stdout.write(f"Usuarios actualizados: {users_actualizados}")
        self.stdout.write(f"Docentes actualizados: {docentes_actualizados}")
        self.stdout.write(f"Representantes actualizados: {reps_actualizados}")
        self.stdout.write(f"Estudiantes actualizados: {estudiantes_actualizados}")
        self.stdout.write(f"Citas actualizadas: {citas_actualizadas}")
        self.stdout.write(self.style.SUCCESS("Todo quedó asignado correctamente."))
