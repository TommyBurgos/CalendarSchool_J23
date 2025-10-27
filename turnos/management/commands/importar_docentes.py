import csv, re
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from user.models import Rol
from turnos.models import PerfilDocente, DisponibilidadSemanal

User = get_user_model()

ABREV_DIA = {"LUN":0,"MAR":1,"MIE":2,"JUE":3,"VIE":4,"SAB":5,"DOM":6}
RANGO_RE = re.compile(r"^\s*(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})\s*$")

def parsear_disponibilidad(cadena):
    """
    'LUN 08:00-10:00|LUN 14:00-16:00|MIE 09:00-11:00' ->
    [(0,'08:00','10:00'), (0,'14:00','16:00'), (2,'09:00','11:00')]
    """
    if not cadena:
        return []
    items = [p.strip() for p in cadena.split("|") if p.strip()]
    resultado = []
    for item in items:
        # Espera 'XXX HH:MM-HH:MM'
        try:
            abrev, rango = item.split(None, 1)
        except ValueError:
            continue
        abrev = abrev.upper()
        if abrev not in ABREV_DIA:
            continue
        m = RANGO_RE.match(rango)
        if not m:
            continue
        ini, fin = m.group(1), m.group(2)
        resultado.append((ABREV_DIA[abrev], ini, fin))
    return resultado

class Command(BaseCommand):
    help = "Importa DOCENTES (usuarios + PerfilDocente) y opcionalmente su DisponibilidadSemanal desde CSV."

    def add_arguments(self, parser):
        parser.add_argument("ruta_csv", type=str, help="Ruta del CSV de docentes")

    def handle(self, *args, **options):
        ruta = options["ruta_csv"]
        try:
            f = open(ruta, newline="", encoding="utf-8")
        except FileNotFoundError:
            raise CommandError(f"No se encontró el archivo: {ruta}")

        reader = csv.DictReader(f)
        rol_doc, _ = Rol.objects.get_or_create(nombre="Docente", defaults={"descripcion":"Docente"})

        creados = actualizados = 0
        franjas_creadas = 0
        for row in reader:
            cedula = (row.get("cedula") or "").strip()
            if not cedula:
                self.stdout.write(self.style.WARNING(f"Fila sin cédula: {row}"))
                continue

            email = (row.get("email") or "").strip().lower() or None
            nombres = (row.get("nombres") or "").strip()
            apellidos = (row.get("apellidos") or "").strip()
            telefono = (row.get("telefono") or "").strip()
            departamento = (row.get("departamento") or "").strip()
            try:
                minutos_por_bloque = int(row.get("minutos_por_bloque") or 20)
            except ValueError:
                minutos_por_bloque = 20
            try:
                maximo_citas_diarias = row.get("maximo_citas_diarias")
                maximo_citas_diarias = int(maximo_citas_diarias) if maximo_citas_diarias not in (None, "",) else None
            except ValueError:
                maximo_citas_diarias = None
            activo = str(row.get("activo") or "1").strip() in ("1","true","True","TRUE")
            disponibilidad_raw = (row.get("disponibilidad") or "").strip()
            reemplazar = str(row.get("reemplazar_disponibilidad") or "0").strip() in ("1","true","True","TRUE")

            # Usuario (username = cedula)
            user = User.objects.filter(cedula=cedula).first()
            if not user:
                user = User.objects.create_user(username=cedula, cedula=cedula, email=email, password="12345678")
                # nombres/apellidos (si tu User los usa)
                cambios = []
                if hasattr(user, "first_name") and nombres:
                    user.first_name = nombres; cambios.append("first_name")
                if hasattr(user, "last_name") and apellidos:
                    user.last_name = apellidos; cambios.append("last_name")
                if cambios:
                    user.save(update_fields=cambios)
                creados += 1
            else:
                cambios = []
                if email and not user.email:
                    user.email = email; cambios.append("email")
                if hasattr(user, "first_name") and nombres and user.first_name != nombres:
                    user.first_name = nombres; cambios.append("first_name")
                if hasattr(user, "last_name") and apellidos and user.last_name != apellidos:
                    user.last_name = apellidos; cambios.append("last_name")
                if cambios:
                    user.save(update_fields=cambios)
                actualizados += 1

            # Rol Docente
            if not user.rol:
                user.rol = rol_doc
                user.save(update_fields=["rol"])

            # PerfilDocente
            perfil, _ = PerfilDocente.objects.get_or_create(usuario=user)
            cambios = []
            if perfil.minutos_por_bloque != minutos_por_bloque:
                perfil.minutos_por_bloque = minutos_por_bloque; cambios.append("minutos_por_bloque")
            if perfil.maximo_citas_diarias != maximo_citas_diarias:
                perfil.maximo_citas_diarias = maximo_citas_diarias; cambios.append("maximo_citas_diarias")
            if perfil.departamento != departamento:
                perfil.departamento = departamento; cambios.append("departamento")
            if perfil.telefono != telefono:
                perfil.telefono = telefono; cambios.append("telefono")
            if perfil.activo != activo:
                perfil.activo = activo; cambios.append("activo")
            if cambios:
                perfil.save(update_fields=cambios)

            # Disponibilidad (opcional)
            if disponibilidad_raw:
                franjas = parsear_disponibilidad(disponibilidad_raw)
                if reemplazar:
                    PerfilDocente.disponibilidades.rel.model.objects.filter(docente=perfil).delete()
                for dia, h_ini, h_fin in franjas:
                    # Evita solapes básicos duplicados exactos
                    existe = PerfilDocente.disponibilidades.rel.model.objects.filter(
                        docente=perfil, dia_semana=dia, hora_inicio=h_ini, hora_fin=h_fin
                    ).exists()
                    if not existe:
                        DisponibilidadSemanal.objects.create(
                            docente=perfil, dia_semana=dia, hora_inicio=h_ini, hora_fin=h_fin
                        )
                        franjas_creadas += 1

        f.close()
        self.stdout.write(self.style.SUCCESS(
            f"Docentes importados. Nuevos: {creados}, Actualizados: {actualizados}, Franjas creadas: {franjas_creadas}"
        ))
