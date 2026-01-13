from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import RegistroForm, LoginForm, PerfilUsuarioForm
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.forms import PasswordChangeForm



def registrar(request):
    print("Ingrese a la funcion registrar")
    if request.method == "POST":
        print("Ingrese al post")
        form = RegistroForm(request.POST)
        print(form)
        print(form.is_valid)
        if form.is_valid():
            print("Ingresé al condicional...")            
            user = form.save()
            print(user)
            messages.success(request, "Cuenta creada. ¡Bienvenido!")
            print("El usuario se creo correctamente")
            login(request, user)
            print("Se logeo, aunque no deberia aun")
            return redirect("login")
    else:
        form = RegistroForm()
        print(form.errors)
    return render(request, "sitioWeb/sign-up.html", {"form": form})

User = get_user_model()
def vista_login(request):
    if request.method == "POST":
        # Puede venir como 'cedula' o como 'email' según el template actual
        identificador = (request.POST.get("cedula") or request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""

        if not identificador or not password:
            messages.error(request, "Ingresa usuario y contraseña.")
            return render(request, "sitioWeb/sign-in.html", {"email": identificador})

        usuarios = User.objects.none()

        # 1) Intentar primero por cédula (multi-institución)
        #    Tu User tiene campo cedula y en save() pones username = cedula
        usuarios_cedula = User.objects.filter(cedula=identificador)
        if usuarios_cedula.exists():
            usuarios = usuarios_cedula
            # Para autenticar usamos username REAL (que es la cédula normalizada)
            user_for_auth = usuarios.first()
            username_auth = user_for_auth.username
        else:
            # 2) Si no hay por cédula, intentamos por email como tenías antes
            usuarios_email = User.objects.filter(email__iexact=identificador)
            if usuarios_email.exists():
                usuarios = usuarios_email
                user_for_auth = usuarios.first()
                username_auth = user_for_auth.username  # puede ser la cédula o lo que tengas guardado
            else:
                messages.error(request, "Credenciales inválidas o usuario inactivo.")
                return render(request, "sitioWeb/sign-in.html", {"email": identificador})

        # Autenticación utilizando username real del usuario encontrado
        user = authenticate(request, username=username_auth, password=password)

        if user is None or not user.is_active:
            messages.error(request, "Credenciales inválidas o usuario inactivo.")
            return render(request, "sitioWeb/sign-in.html", {"email": identificador})

        # Manejo "Recordarme"
        if request.POST.get("remember") != "on":
            request.session.set_expiry(0)

        # Manejo seguro de ?next=
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            next_url = None

        # --- LÓGICA DE INSTITUCIÓN ---

        # Recolectar instituciones distintas asociadas a esos usuarios
        instituciones = []
        for u in usuarios.select_related("institucion"):
            if getattr(u, "institucion", None) and u.institucion not in instituciones:
                instituciones.append(u.institucion)

        # Caso 0 instituciones (aún no has asignado) → dejamos pasar como antes
        if not instituciones:
            login(request, user)
            if user.debe_cambiar_password:
                if next_url:
                    request.session["next_after_password_change"] = next_url
                return redirect("cambiar_password_forzado")

            if next_url:
                return redirect(next_url)
            return post_login_redirect(user)

        # Caso 1 sola institución → guardamos en sesión y seguimos normal
        if len(instituciones) == 1:
            request.session["institucion_id"] = instituciones[0].id
            login(request, user)
            if user.debe_cambiar_password:
                if next_url:
                    request.session["next_after_password_change"] = next_url
                return redirect("cambiar_password_forzado")

            if next_url:
                return redirect(next_url)
            return post_login_redirect(user)

        # Caso varias instituciones (escenario futuro):
        # Guardamos datos en sesión y redirigimos a una vista que tú crearás
        request.session["pending_user_id"] = user.id
        request.session["login_next"] = next_url
        return redirect("seleccionar_institucion")  # luego la implementamos

    # GET
    return render(request, "sitioWeb/sign-in.html")

def seleccionar_institucion(request):
    cedula = request.session.get("login_cedula")
    if not cedula:
        return redirect("login")

    usuarios = User.objects.filter(cedula=cedula)

    if request.method == "POST":
        inst_id = request.POST.get("institucion")
        usuario = usuarios.filter(institucion_id=inst_id).first()
        if usuario:
            request.session["institucion_id"] = inst_id
            login(request, usuario)
            return redirect("dashboard")

    return render(request, "user/seleccionar_institucion.html", {
        "usuarios": usuarios
    })


def logout_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada.")
    return redirect("login")

@login_required
def dashboard(request):
    print("Estoy en la funcion de vista del admin dashboard")
    return render(request, "dashboard_admin.html")

@login_required
def mi_perfil(request):
    base = "base.html"
    rol = getattr(getattr(request.user, "rol", None), "nombre", "")
    if rol == "Docente":
        base = "docente/base.html"
    elif rol == "Representante":
        base = "representante/base.html"
    u = request.user
    if request.method == "POST":
        form = PerfilUsuarioForm(request.POST, request.FILES, instance=u)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado correctamente.")
            return redirect("mi_perfil")
    else:
        form = PerfilUsuarioForm(instance=u)

    # Datos auxiliares por rol (opcionales)
    perfil_docente = getattr(u, "perfil_docente", None)
    relaciones = getattr(u, "relaciones_representacion", None)

    context = {
        "form": form,
        "perfil_docente": perfil_docente,
        "relaciones": relaciones.all() if relaciones else [],
        "base_template": base,
    }
    return render(request, "mi_perfil.html", context)

def post_login_redirect(user, fallback="dashboard"):    
    rol = getattr(getattr(user, "rol", None), "nombre", "")

    if rol == "Docente":
        return redirect("dashboard_docente")
    if rol == "Representante":
        return redirect("rep_buscar")
    if rol == "Administrador":
        return redirect("dashboard_admin")
    if rol == "DocenteAdministrador":
        return redirect("dashboard_admin")

    # Sin rol o rol desconocido
    return redirect(fallback)


@login_required
def cambiar_password_forzado(request):
    if not request.user.debe_cambiar_password:
        return redirect("dashboard")

    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            user.debe_cambiar_password = False
            user.save(update_fields=["debe_cambiar_password"])
            update_session_auth_hash(request, user)
            messages.success(request, "Contraseña actualizada correctamente.")
            return redirect("dashboard")
    else:
        form = PasswordChangeForm(request.user)

    def _get_base_template(user):
        if user.is_superuser or (user.rol and user.rol.nombre in ["Administrador", "DocenteAdministrador"]):
            return "base.html"
        if user.rol and user.rol.nombre == "Docente":
            return "docente/base.html"
        if user.rol and user.rol.nombre == "Representante":
            return "representante/base.html"
        return "base.html"

    base_template = _get_base_template(request.user)

    return render(
        request,
        "user/cambiar_password_forzado.html",
        {
            "form": form,
            "base_template": base_template,
        }
    )    

@login_required
def cambiar_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Contraseña cambiada correctamente.")
            return redirect("mi_perfil")
    else:
        form = PasswordChangeForm(request.user)

    def _get_base_template(user):
        if user.is_superuser or (user.rol and user.rol.nombre in ["Administrador", "DocenteAdministrador"]):
            return "base.html"
        if user.rol and user.rol.nombre == "Docente":
            return "docente/base.html"
        if user.rol and user.rol.nombre == "Representante":
            return "representante/base.html"
        return "base.html"

    base_template = _get_base_template(request.user)

    return render(request,
        "user/cambiar_password_forzado.html",
        {
            "form": form,
            "base_template": base_template,
        })
