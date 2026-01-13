from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Rol, Institucion
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class RegistroForm(UserCreationForm):
    # username no se muestra, se asigna desde cédula
    username = forms.CharField(required=False, widget=forms.HiddenInput())

    cedula = forms.CharField(
        label="Cédula",
        max_length=20,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ingrese su cédula",
        })
    )

    codigo_institucion = forms.CharField(
        label="Código de la institución",
        max_length=50,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ej: UEDSM-01",
        })
    )

    first_name = forms.CharField(
        label="Nombres",
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    last_name = forms.CharField(
        label="Apellidos",
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = User
        fields = (
            "cedula",
            "first_name",
            "last_name",
            "password1",
            "password2",
            "username",
        )

    def clean_codigo_institucion(self):
        codigo = self.cleaned_data["codigo_institucion"].strip()
        try:
            return Institucion.objects.get(codigo=codigo)
        except Institucion.DoesNotExist:
            raise forms.ValidationError("Código de institución inválido.")

    def save(self, commit=True):
        user = super().save(commit=False)

        cedula = self.cleaned_data["cedula"]
        institucion = self.cleaned_data["codigo_institucion"]

        # username = cédula
        user.username = cedula
        user.cedula = cedula
        user.institucion = institucion

        # Rol Representante
        rol_rep, _ = Rol.objects.get_or_create(
            nombre="Representante",
            defaults={"descripcion": "Padre/madre/representante"},
        )
        user.rol = rol_rep

        # Forzar cambio de contraseña en primer login
        user.debe_cambiar_password = False  # porque ya la define él mismo aquí

        if commit:
            user.save()

        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={
            "class": "form-control border-0 bg-light rounded-end ps-1",
            "placeholder": "E-mail",
            "id": "exampleInputEmail1",
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control border-0 bg-light rounded-end ps-1",
            "placeholder": "*********",
            "id": "inputPassword5",
        })
    )
    username = forms.EmailField(                      # <- email como username
        label="Email address",
        widget=forms.EmailInput(attrs={
            "class": "form-control border-0 bg-light rounded-end ps-1",
            "placeholder": "E-mail",
            "id": "exampleInputEmail1",
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control border-0 bg-light rounded-end ps-1",
            "placeholder": "*********",
            "id": "inputPassword5",
        })
    )

class PerfilUsuarioForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "cedula", "email", "imgPerfil"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class":"form-control", "placeholder":"Nombres"}),
            "last_name": forms.TextInput(attrs={"class":"form-control", "placeholder":"Apellidos"}),
            "cedula": forms.TextInput(attrs={"class":"form-control", "readonly":"readonly"}),  # username
            "email": forms.EmailInput(attrs={"class":"form-control", "placeholder":"correo@dominio.com"}),
            "imgPerfil": forms.FileInput(attrs={"class":"form-control"})
        }

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        return email or None
    
class UsuarioCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ("email", "cedula", "first_name", "last_name", "rol", "is_active", "institucion")

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        # username = cedula (refuerzo por si cambia el orden de llamadas)
        user.username = user.cedula
        # password por defecto si no enviaron:
        raw = self.cleaned_data.get("password1") or "12345678"
        user.set_password(raw)
        if commit:
            user.save()
        return user

class UsuarioChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(label="Password (hash de solo lectura)")
    password1 = forms.CharField(label="Nueva contraseña", widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label="Confirmar nueva", widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ("email", "cedula", "first_name", "last_name", "rol", "is_active", "password")

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        # sincroniza username con la cédula editada
        if user.cedula:
            user.username = user.cedula
        p1 = self.cleaned_data.get("password1")
        if p1:
            user.set_password(p1)
        if commit:
            user.save()
        return user