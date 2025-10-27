from django import forms
from django.utils import timezone
from .models import PerfilDocente


class BuscarSlotsForm(forms.Form):
    docente = forms.ModelChoiceField(
        queryset=PerfilDocente.objects.filter(activo=True).select_related("usuario"),
        label="Docente",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    fecha = forms.DateField(
        label="Fecha",
        input_formats=["%Y-%m-%d"],  # ✅ coincide con <input type="date">
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )

    def clean_fecha(self):
        f = self.cleaned_data["fecha"]
        if f < timezone.localdate():
            raise forms.ValidationError("Seleccione una fecha futura.")
        return f

class ReservaCitaForm(forms.Form):
    docente_id = forms.IntegerField(widget=forms.HiddenInput())
    inicio_iso = forms.CharField(widget=forms.HiddenInput()) # ISO 8601
    curso_estudiante = forms.CharField(label="Curso", max_length=100, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "p.ej. 8vo A"}))
    nombre_estudiante = forms.CharField(label="Nombre del estudiante", max_length=120, widget=forms.TextInput(attrs={"class": "form-control"}))
    motivo = forms.CharField(label="Motivo", widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}))

class BuscarSemanaForm(forms.Form):
    docente = forms.ModelChoiceField(
        queryset=PerfilDocente.objects.filter(activo=True).select_related("usuario"),
        label="Docente",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    # Punto de partida: una fecha cualquiera de la semana a consultar
    fecha = forms.DateField(
        label="Semana de",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )

    def clean_fecha(self):
        f = self.cleaned_data["fecha"]
        # Permite ver semanas pasadas si quisieras; para solo futuras, descomenta:
        # if f < timezone.localdate(): raise forms.ValidationError("Seleccione una fecha futura.")
        return f
