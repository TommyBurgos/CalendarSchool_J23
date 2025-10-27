from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Rol
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class RegistroForm(UserCreationForm):
    # ocultamos username para que no bloquee la validación
    username = forms.CharField(required=False, widget=forms.HiddenInput())
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password1", "password2", "username")

    def clean(self):
        data = super().clean()
        # si no viene username, lo igualamos al email
        if not data.get("username") and data.get("email"):
            data["username"] = data["email"]
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data.get("username") or self.cleaned_data["email"]
        rol_rep, _ = Rol.objects.get_or_create(
            nombre="Representante",
            defaults={"descripcion": "Padre/madre/representante"},
        )
        user.rol = rol_rep
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
        fields = ("email", "cedula", "first_name", "last_name", "rol", "is_active")

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