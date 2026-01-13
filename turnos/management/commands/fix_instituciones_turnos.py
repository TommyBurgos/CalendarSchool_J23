from django.core.management.base import BaseCommand
from turnos.models import DisponibilidadSemanal


class Command(BaseCommand):
    help = "Corrige registros de turnos con institucion NULL copiando desde el docente"

    def handle(self, *args, **options):
        qs = (
            DisponibilidadSemanal.objects
            .filter(institucion__isnull=True)
            .select_related("docente")
        )

        total = 0

        for obj in qs:
            if obj.docente and obj.docente.institucion:
                obj.institucion = obj.docente.institucion
                obj.save(update_fields=["institucion"])
                total += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✔ Institución corregida en {total} disponibilidades."
            )
        )
