import csv
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from user.models import Rol
from turnos.models import Estudiante, RelacionRepresentacion, FuenteRelacion

User = get_user_model()

class Command(BaseCommand):
    help = "Importa estudiantes (y opcionalmente relaciones con representantes) desde un CSV."

    def add_arguments(self, parser):
        parser.add_argument("ruta_csv", type=str, help="Ruta del archivo CSV a importar")

    def handle(self, *args, **options):
        ruta = options["ruta_csv"]
        total_est = total_rel = 0

        try:
            with open(ruta, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rol_rep, _ = Rol.objects.get_or_create(nombre="Representante", defaults={"descripcion":"Padre/Madre/Apoderado"})

                for row in reader:
                    cedula = (row.get("cedula") or "").strip()
                    nombre = (row.get("nombre") or "").strip()
                    curso = (row.get("curso") or "").strip()

                    if not cedula or not nombre:
                        self.stdout.write(self.style.WARNING(f"Fila incompleta (cedula/nombre): {row}"))
                        continue

                    # Estudiante (create/update)
                    est, created = Estudiante.objects.get_or_create(
                        cedula=cedula,
                        defaults={"nombre": nombre, "curso": curso}
                    )
                    if not created:
                        # Actualiza cambios de nombre/curso si vinieron diferentes
                        cambios = []
                        if est.nombre != nombre:
                            est.nombre = nombre; cambios.append("nombre")
                        if curso and est.curso != curso:
                            est.curso = curso; cambios.append("curso")
                        if cambios:
                            est.save(update_fields=cambios)
                    total_est += 1

                    # Representante (opcional): por cédula o email
                    rep_cedula = (row.get("representante_cedula") or "").strip()
                    rep_email = (row.get("representante_email") or "").strip().lower()

                    if not rep_cedula and not rep_email:
                        # Sin datos del representante -> solo estudiante
                        continue

                    rep = None
                    if rep_cedula:
                        rep = User.objects.filter(cedula=rep_cedula).first()
                    if not rep and rep_email:
                        rep = User.objects.filter(email=rep_email).first()

                    if not rep:
                        # Crear usuario: preferimos cédula como username si existe
                        if rep_cedula:
                            rep = User.objects.create_user(
                                username=rep_cedula, cedula=rep_cedula, email=rep_email or None, password="12345678"
                            )
                        else:
                            rep = User.objects.create_user(
                                username=rep_email, email=rep_email, password="12345678"
                            )

                    # Completar datos faltantes y asignar rol
                    actualizar = []
                    if rep_cedula and not getattr(rep, "cedula", None):
                        rep.cedula = rep_cedula; actualizar.append("cedula")
                    if rep_email and not rep.email:
                        rep.email = rep_email; actualizar.append("email")
                    if not rep.rol:
                        rep.rol = rol_rep; actualizar.append("rol")
                    if actualizar:
                        rep.save(update_fields=actualizar)

                    # Relación estudiante-representante
                    parentesco = (row.get("parentesco") or "").strip()
                    verificado = (row.get("verificado") or "0").strip() in ["1", "true", "True"]
                    RelacionRepresentacion.objects.update_or_create(
                        estudiante=est,
                        representante=rep,
                        defaults={
                            "parentesco": parentesco,
                            "verificado": verificado,
                            "fuente": FuenteRelacion.IMPORT,
                            "activo": True,
                        },
                    )
                    total_rel += 1

            self.stdout.write(self.style.SUCCESS(
                f"Importación completada: {total_est} estudiantes, {total_rel} relaciones."
            ))

        except FileNotFoundError:
            raise CommandError(f"No se encontró el archivo: {ruta}")
