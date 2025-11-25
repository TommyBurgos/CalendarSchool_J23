from django import forms
from django.utils import timezone
from .models import PerfilDocente
from turnos.models import RelacionRepresentacion, Materia, Curso


class BuscarSlotsForm(forms.Form):
    docente = forms.ModelChoiceField(
        queryset=PerfilDocente.objects.filter(activo=True).select_related("usuario"),
        label="Docente",
        widget=forms.Select(attrs={"class": "form-select"}),
    )    

    def clean_fecha(self):
        f = self.cleaned_data["fecha"]
        if f < timezone.localdate():
            raise forms.ValidationError("Seleccione una fecha futura.")
        return f

class ReservaCitaForm(forms.Form):
    docente_id = forms.IntegerField(widget=forms.HiddenInput())
    inicio_iso = forms.CharField(widget=forms.HiddenInput())

    estudiante_rel = forms.ModelChoiceField(
        queryset=None,
        label="Estudiante",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    motivo = forms.CharField(
        label="Motivo",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3})
    )

    def __init__(self, *args, representante=None, **kwargs):
        super().__init__(*args, **kwargs)

        if representante:
            self.fields["estudiante_rel"].queryset = RelacionRepresentacion.objects.filter(
                representante=representante, activo=True
            ).select_related("estudiante")


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

class BuscarDocenteMateriaCursoForm(forms.Form):
    materia = forms.ModelChoiceField(
        queryset=Materia.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    curso = forms.ModelChoiceField(
    queryset=Curso.objects.all(),
    required=False,
    widget=forms.Select(attrs={"class": "form-select"})
)
