from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import RegistroForm, LoginForm, PerfilUsuarioForm
from django.utils.http import url_has_allowed_host_and_scheme

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

def vista_login(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""
        user = authenticate(request, username=email, password=password)

        if user is not None and user.is_active:
            # "Recordarme": si NO está marcado, la sesión expira al cerrar el navegador
            if request.POST.get("remember") != "on":
                request.session.set_expiry(0)

            login(request, user)

            # Manejo seguro de ?next=
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)

            return post_login_redirect(user)

        messages.error(request, "Credenciales inválidas o usuario inactivo.")
        # Mantener el email tipeado
        return render(request, "sitioWeb/sign-in.html", {"email": email})

    # GET
    return render(request, "sitioWeb/sign-in.html")

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
    """Redirige según el rol del usuario."""
    rol = getattr(getattr(user, "rol", None), "nombre", "")

    if rol == "Docente":
        return redirect("dashboard_docente")
    if rol == "Representante":
        return redirect("rep_buscar")
    if rol == "Administrador":
        return redirect("dashboard")  # tu panel admin

    # Sin rol o rol desconocido
    return redirect(fallback)