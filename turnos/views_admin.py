import csv, io, re
from django.contrib import messages
from django.contrib.auth import get_user_model
from user.decorators import requiere_rol
from user.models import Rol
from turnos.forms import CargaCSVForm
from turnos.models import Estudiante, RelacionRepresentacion, FuenteRelacion
from django.http import HttpResponse

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from .models import PerfilDocente, DisponibilidadSemanal, ExcepcionDisponibilidad, TipoExcepcion, FeriadoInstitucional
from .forms import PerfilDocenteForm, DisponibilidadSemanalForm, ExcepcionDisponibilidadForm, BloqueoMasivoForm

from turnos.forms import CargaCSVDocentesForm

from datetime import timedelta, datetime
from django.db import transaction
from django.utils import timezone
from user.decorators import requiere_roles



User = get_user_model()

@requiere_roles("Administrador", "DocenteAdministrador")
def cargar_estudiantes(request):
    if request.method == "POST":
        form = CargaCSVForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = form.cleaned_data["archivo"]
            try:
                data = archivo.read().decode("utf-8")
            except UnicodeDecodeError:
                messages.error(request, "El archivo debe estar en UTF-8.")
                return redirect("cargar_estudiantes")

            reader = csv.DictReader(io.StringIO(data))
            total_est = total_rel = 0
            rol_rep, _ = Rol.objects.get_or_create(nombre="Representante", defaults={"descripcion":"Padre/Madre/Apoderado"})

            for row in reader:
                cedula = (row.get("cedula") or "").strip()
                nombre = (row.get("nombre") or "").strip()
                curso = (row.get("curso") or "").strip()

                if not cedula or not nombre:
                    continue

                est, created = Estudiante.objects.get_or_create(
                    cedula=cedula, defaults={"nombre": nombre, "curso": curso}
                )
                if not created:
                    cambios = []
                    if est.nombre != nombre:
                        est.nombre = nombre; cambios.append("nombre")
                    if curso and est.curso != curso:
                        est.curso = curso; cambios.append("curso")
                    if cambios:
                        est.save(update_fields=cambios)
                total_est += 1

                rep_cedula = (row.get("representante_cedula") or "").strip()
                rep_email = (row.get("representante_email") or "").strip().lower()

                if not rep_cedula and not rep_email:
                    # Solo carga estudiante
                    continue

                rep = None
                if rep_cedula:
                    rep = User.objects.filter(cedula=rep_cedula).first()
                if not rep and rep_email:
                    rep = User.objects.filter(email=rep_email).first()

                if not rep:
                    if rep_cedula:
                        rep = User.objects.create_user(
                            username=rep_cedula, cedula=rep_cedula, email=rep_email or None, password="12345678"
                        )
                    else:
                        rep = User.objects.create_user(
                            username=rep_email, email=rep_email, password="12345678"
                        )

                actualizar = []
                if rep_cedula and not getattr(rep, "cedula", None):
                    rep.cedula = rep_cedula; actualizar.append("cedula")
                if rep_email and not rep.email:
                    rep.email = rep_email; actualizar.append("email")
                if not rep.rol:
                    rep.rol = rol_rep; actualizar.append("rol")
                if actualizar:
                    rep.save(update_fields=actualizar)

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

            messages.success(request, f"Se importaron {total_est} estudiantes y {total_rel} relaciones.")
            return redirect("cargar_estudiantes")
    else:
        form = CargaCSVForm()

    return render(request, "cargar_estudiantes.html", {"form": form})


@requiere_roles("Administrador", "DocenteAdministrador")
def descargar_formato_estudiantes(request):
    contenido = (
        "cedula,nombre,curso,representante_cedula,representante_email,parentesco,verificado\n"
        "0912345678,Ana Pérez,8vo A,1102345678,rep1@demo.com,Madre,1\n"
        "0912345679,Carlos Gómez,8vo A,1109876543,rep2@demo.com,Padre,0\n"
        "0912345680,Sofía Torres,9no B,1103456789,,Tía,0\n"
    )
    response = HttpResponse(contenido, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="formato_estudiantes.csv"'
    return response

@requiere_roles("Administrador", "DocenteAdministrador")
def listar_docentes(request):
    # Usuarios con rol Docente o candidatos a serlo (filtro rápido por texto)
    q = (request.GET.get("q") or "").strip().lower()
    rol_doc, _ = Rol.objects.get_or_create(nombre="Docente")
    usuarios = User.objects.filter(Q(rol=rol_doc) | Q(perfil_docente__isnull=False)).select_related("perfil_docente","rol")
    if q:
        usuarios = usuarios.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    usuarios = usuarios.order_by("first_name","last_name","email")
    return render(request, "docentes_listar.html", {"usuarios": usuarios, "q": q})

@requiere_roles("Administrador", "DocenteAdministrador")
def editar_perfil_docente(request, user_id):
    rol_doc, _ = Rol.objects.get_or_create(nombre="Docente")
    usuario = get_object_or_404(User, pk=user_id)
    perfil, _ = PerfilDocente.objects.get_or_create(usuario=usuario)
    if not usuario.rol:
        usuario.rol = rol_doc; usuario.save(update_fields=["rol"])
    if request.method == "POST":
        form = PerfilDocenteForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil de docente guardado.")
            return redirect("gestionar_disponibilidad_docente", docente_id=perfil.id)
    else:
        form = PerfilDocenteForm(instance=perfil)
    return render(request, "docente_editar.html", {"usuario": usuario, "form": form, "perfil": perfil})

@requiere_roles("Administrador", "DocenteAdministrador")
def gestionar_disponibilidad_docente(request, docente_id):
    docente = get_object_or_404(PerfilDocente, pk=docente_id)
    form_disp = DisponibilidadSemanalForm(request.POST or None)
    form_exc = ExcepcionDisponibilidadForm(request.POST or None)

    if request.method == "POST":
        # Alta disponibilidad semanal
        if "guardar_disp" in request.POST and form_disp.is_valid():
            disp = form_disp.save(commit=False)
            disp.docente = docente
            # Regla simple anti-solape de disponibilidad (mismo día)
            solapa = DisponibilidadSemanal.objects.filter(
                docente=docente,
                dia_semana=disp.dia_semana,
                hora_inicio__lt=disp.hora_fin,
                hora_fin__gt=disp.hora_inicio
            ).exists()
            if solapa:
                messages.error(request, "La franja se solapa con otra existente.")
            else:
                disp.full_clean(); disp.save()
                messages.success(request, "Franja semanal agregada.")
            return redirect("gestionar_disponibilidad_docente", docente_id=docente.id)

        # Alta excepción (bloqueo/extra)
        if "guardar_exc" in request.POST and form_exc.is_valid():
            exc = form_exc.save(commit=False)
            exc.docente = docente
            exc.full_clean(); exc.save()
            messages.success(request, "Excepción guardada.")
            return redirect("gestionar_disponibilidad_docente", docente_id=docente.id)

    disponibilidades = docente.disponibilidades.order_by("dia_semana","hora_inicio")
    excepciones = docente.excepciones.order_by("-fecha","hora_inicio")[:30]

    return render(request, "docente_disponibilidad.html", {
        "docente": docente,
        "disponibilidades": disponibilidades,
        "excepciones": excepciones,
        "form_disp": form_disp,
        "form_exc": form_exc,
    })

@requiere_roles("Administrador", "DocenteAdministrador")
def eliminar_disponibilidad(request, disp_id):
    disp = get_object_or_404(DisponibilidadSemanal, pk=disp_id)
    docente_id = disp.docente.id
    disp.delete()
    messages.info(request, "Franja eliminada.")
    return redirect("gestionar_disponibilidad_docente", docente_id=docente_id)

@requiere_roles("Administrador", "DocenteAdministrador")
def eliminar_excepcion(request, exc_id):
    exc = get_object_or_404(ExcepcionDisponibilidad, pk=exc_id)
    docente_id = exc.docente.id
    exc.delete()
    messages.info(request, "Excepción eliminada.")
    return redirect("gestionar_disponibilidad_docente", docente_id=docente_id)

ABREV_DIA = {"LUN":0,"MAR":1,"MIE":2,"JUE":3,"VIE":4,"SAB":5,"DOM":6}
RANGO_RE = re.compile(r"^\s*(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})\s*$")

def _parsear_disponibilidad(cadena:str):
    if not cadena: 
        return [], []
    items = [p.strip() for p in cadena.split("|") if p.strip()]
    resultado, errores = [], []
    for seg in items:
        try:
            abrev, rango = seg.split(None, 1)
        except ValueError:
            errores.append(f"Formato inválido: '{seg}'"); 
            continue
        abrev = abrev.upper()
        if abrev not in ABREV_DIA:
            errores.append(f"Día inválido: '{abrev}'"); 
            continue
        m = RANGO_RE.match(rango)
        if not m:
            errores.append(f"Rango inválido: '{rango}' (usa HH:MM-HH:MM)")
            continue
        ini, fin = m.group(1), m.group(2)
        if ini >= fin:
            errores.append(f"Inicio >= fin en '{seg}'")
            continue
        resultado.append((ABREV_DIA[abrev], ini, fin))
    return resultado, errores

@requiere_roles("Administrador", "DocenteAdministrador")
def cargar_docentes(request):
    if request.method == "POST":
        form = CargaCSVDocentesForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                data = form.cleaned_data["archivo"].read().decode("utf-8")
            except UnicodeDecodeError:
                messages.error(request, "El archivo debe estar en UTF-8.")
                return redirect("cargar_docentes")

            reader = csv.DictReader(io.StringIO(data))
            rol_doc, _ = Rol.objects.get_or_create(nombre="Docente", defaults={"descripcion":"Docente"})
            creados = actualizados = franjas_creadas = 0

            for row in reader:
                cedula = (row.get("cedula") or "").strip()
                if not cedula:
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
                    mcd = row.get("maximo_citas_diarias")
                    maximo_citas_diarias = int(mcd) if mcd not in (None,""," ") else None
                except ValueError:
                    maximo_citas_diarias = None
                activo = str(row.get("activo") or "1").strip() in ("1","true","True","TRUE")
                disponibilidad_raw = (row.get("disponibilidad") or "").strip()
                reemplazar = str(row.get("reemplazar_disponibilidad") or "0").strip() in ("1","true","True","TRUE")

                # Usuario (username = cedula)
                user = User.objects.filter(cedula=cedula).first()
                if not user:
                    user = User.objects.create_user(username=cedula, cedula=cedula, email=email, password="12345678")
                    cambios = []
                    if hasattr(user,"first_name") and nombres: user.first_name = nombres; cambios.append("first_name")
                    if hasattr(user,"last_name") and apellidos: user.last_name = apellidos; cambios.append("last_name")
                    if cambios: user.save(update_fields=cambios)
                    creados += 1
                else:
                    cambios = []
                    if email and not user.email: user.email = email; cambios.append("email")
                    if hasattr(user,"first_name") and nombres and user.first_name != nombres:
                        user.first_name = nombres; cambios.append("first_name")
                    if hasattr(user,"last_name") and apellidos and user.last_name != apellidos:
                        user.last_name = apellidos; cambios.append("last_name")
                    if cambios: user.save(update_fields=cambios)
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

                # Disponibilidad inicial (opcional)
                # Disponibilidad inicial (opcional)
                if disponibilidad_raw:
                    franjas, errs = _parsear_disponibilidad(disponibilidad_raw)
                    if errs:
                        # Acumula errores con número de fila (usa reader.line_num si prefieres)
                        messages.warning(request, f"Fila con cédula {cedula}: {', '.join(errs[:3])}" + (" ..." if len(errs) > 3 else ""))
                    else:
                        if reemplazar:
                            DisponibilidadSemanal.objects.filter(docente=perfil).delete()
                        for dia, h_ini, h_fin in franjas:
                            existe = DisponibilidadSemanal.objects.filter(
                                docente=perfil, dia_semana=dia, hora_inicio=h_ini, hora_fin=h_fin
                            ).exists()
                            if not existe:
                                DisponibilidadSemanal.objects.create(
                                    docente=perfil, dia_semana=dia, hora_inicio=h_ini, hora_fin=h_fin
                                )
                                franjas_creadas += 1

            messages.success(request, f"Docentes cargados. Nuevos: {creados}, Actualizados: {actualizados}, Franjas creadas: {franjas_creadas}.")
            return redirect("cargar_docentes")
    else:
        form = CargaCSVDocentesForm()

    return render(request, "cargar_docentes.html", {"form": form})

@requiere_roles("Administrador", "DocenteAdministrador")
def formato_docentes(request):
    contenido = (
        "cedula,email,nombres,apellidos,telefono,departamento,minutos_por_bloque,maximo_citas_diarias,activo,disponibilidad,reemplazar_disponibilidad\n"
        "1102345678,doc1@demo.com,María,Lopez,0999999999,Matemática,20,8,1,LUN 08:00-10:00|MAR 09:00-11:00,1\n"
        "1103456789,doc2@demo.com,Juan,Perez,0988888888,Inglés,20,6,1,,0\n"
    )
    resp = HttpResponse(contenido, content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="formato_docentes.csv"'
    return resp


def _daterange(d1, d2):
    cur = d1
    while cur <= d2:
        yield cur
        cur += timedelta(days=1)

@requiere_roles("Administrador", "DocenteAdministrador")
@transaction.atomic
def bloqueo_masivo(request):
    if request.method == "POST":
        form = BloqueoMasivoForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data["nombre"]
            fi = form.cleaned_data["fecha_inicio"]
            ff = form.cleaned_data["fecha_fin"]
            hi = form.cleaned_data.get("hora_inicio")
            hf = form.cleaned_data.get("hora_fin")
            aplicar_a = form.cleaned_data["aplicar_a"]
            depto = (form.cleaned_data.get("departamento") or "").strip()
            reemplazar = form.cleaned_data["reemplazar"]

            # Docentes destino
            docentes = PerfilDocente.objects.filter(activo=True)
            if aplicar_a == "departamento":
                docentes = docentes.filter(departamento__iexact=depto)

            total_doc = docentes.count()
            if total_doc == 0:
                messages.warning(request, "No hay docentes que coincidan con el filtro.")
                return redirect("bloqueo_masivo")

            # Registrar feriado (opcional) para referencia
            feriado = FeriadoInstitucional.objects.create(
                nombre=nombre,
                fecha_inicio=fi, fecha_fin=ff,
                hora_inicio=hi, hora_fin=hf
            )

            creadas = 0
            for fecha in _daterange(fi, ff):
                for d in docentes:
                    qs = ExcepcionDisponibilidad.objects.filter(docente=d, fecha=fecha, tipo=TipoExcepcion.BLOQUEO)
                    if reemplazar:
                        qs.delete()
                    # Evitar duplicado exacto
                    existe = qs.filter(hora_inicio=hi or datetime.min.time(), hora_fin=hf or datetime.max.time()).exists() if (hi and hf) else qs.filter(hora_inicio__isnull=False, hora_fin__isnull=False, hora_inicio__lte="00:00", hora_fin__gte="23:59").exists()
                    # Simplifiquemos: si no se especifica hora => bloquea día completo 00:00–23:59
                    h_ini = hi or datetime.strptime("00:00","%H:%M").time()
                    h_fin = hf or datetime.strptime("23:59","%H:%M").time()
                    if not ExcepcionDisponibilidad.objects.filter(docente=d, fecha=fecha, tipo=TipoExcepcion.BLOQUEO, hora_inicio=h_ini, hora_fin=h_fin).exists():
                        ExcepcionDisponibilidad.objects.create(
                            docente=d, fecha=fecha,
                            hora_inicio=h_ini, hora_fin=h_fin,
                            tipo=TipoExcepcion.BLOQUEO,
                            motivo=nombre
                        )
                        creadas += 1

            messages.success(request, f"Bloqueo aplicado: {feriado.nombre}. Docentes: {total_doc}. Excepciones creadas: {creadas}.")
            return redirect("bloqueo_masivo")
    else:
        form = BloqueoMasivoForm()

    return render(request, "bloqueo_masivo.html", {"form": form})
