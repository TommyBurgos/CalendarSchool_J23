from django.core.management.base import BaseCommand
from turnos.models import RelacionRepresentacion


class Command(BaseCommand):
    help = "Asigna institucion a Relaciones de Representacion que la tengan NULL"

    def handle(self, *args, **options):
        qs = RelacionRepresentacion.objects.filter(
            institucion__isnull=True,
            representante__institucion__isnull=False,
        ).select_related("representante")

        total = qs.count()
        self.stdout.write(f"Relaciones a corregir: {total}")

        for rel in qs:
            rel.institucion = rel.representante.institucion
            rel.save(update_fields=["institucion"])

        self.stdout.write(self.style.SUCCESS("Proceso terminado correctamente"))
