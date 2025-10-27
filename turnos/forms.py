from django import forms
from .models import PerfilDocente, EstadoCita, PerfilDocente, DisponibilidadSemanal, ExcepcionDisponibilidad

class FiltroCitasForm(forms.Form):
    fecha = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="Fecha"
    )
    docente = forms.ModelChoiceField(
        queryset=PerfilDocente.objects.filter(activo=True).select_related("usuario"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Docente"
    )
    estado = forms.ChoiceField(
        required=False,
        choices=[("", "Todos")] + list(EstadoCita.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Estado"
    )

class CargaCSVForm(forms.Form):
    archivo = forms.FileField(label="Archivo CSV", widget=forms.FileInput(attrs={"class": "form-control"}))


class PerfilDocenteForm(forms.ModelForm):
    class Meta:
        model = PerfilDocente
        fields = ["minutos_por_bloque", "maximo_citas_diarias", "departamento", "telefono", "activo"]
        widgets = {
            "minutos_por_bloque": forms.NumberInput(attrs={"class":"form-control","min":"5","step":"5"}),
            "maximo_citas_diarias": forms.NumberInput(attrs={"class":"form-control","min":"1"}),
            "departamento": forms.TextInput(attrs={"class":"form-control"}),
            "telefono": forms.TextInput(attrs={"class":"form-control"}),
            "activo": forms.CheckboxInput(attrs={"class":"form-check-input"}),
        }

class DisponibilidadSemanalForm(forms.ModelForm):
    class Meta:
        model = DisponibilidadSemanal
        fields = ["dia_semana", "hora_inicio", "hora_fin"]
        widgets = {
            "dia_semana": forms.Select(attrs={"class":"form-select"}),
            "hora_inicio": forms.TimeInput(attrs={"type":"time","class":"form-control"}),
            "hora_fin": forms.TimeInput(attrs={"type":"time","class":"form-control"}),
        }

class ExcepcionDisponibilidadForm(forms.ModelForm):
    class Meta:
        model = ExcepcionDisponibilidad
        fields = ["fecha","hora_inicio","hora_fin","tipo","motivo"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type":"date","class":"form-control"}),
            "hora_inicio": forms.TimeInput(attrs={"type":"time","class":"form-control"}),
            "hora_fin": forms.TimeInput(attrs={"type":"time","class":"form-control"}),
            "tipo": forms.Select(attrs={"class":"form-select"}),
            "motivo": forms.TextInput(attrs={"class":"form-control","placeholder":"Opcional"}),
        }

class CargaCSVDocentesForm(forms.Form):
    archivo = forms.FileField(label="Archivo CSV de Docentes", widget=forms.FileInput(attrs={"class":"form-control"}))

class BloqueoMasivoForm(forms.Form):
    nombre = forms.CharField(label="Nombre del feriado/evento", max_length=120, widget=forms.TextInput(attrs={"class":"form-control", "placeholder":"Ej. Feriado de Fundación"}))
    fecha_inicio = forms.DateField(widget=forms.DateInput(attrs={"type":"date","class":"form-control"}))
    fecha_fin = forms.DateField(widget=forms.DateInput(attrs={"type":"date","class":"form-control"}))
    hora_inicio = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type":"time","class":"form-control"}))
    hora_fin = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type":"time","class":"form-control"}))
    aplicar_a = forms.ChoiceField(choices=[("todos","Todos los docentes"), ("departamento","Por departamento")], widget=forms.Select(attrs={"class":"form-select"}))
    departamento = forms.CharField(required=False, widget=forms.TextInput(attrs={"class":"form-control","placeholder":"Ej. Matemática"}))
    reemplazar = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput(attrs={"class":"form-check-input"}))

    def clean(self):
        data = super().clean()
        fi, ff = data.get("fecha_inicio"), data.get("fecha_fin")
        hi, hf = data.get("hora_inicio"), data.get("hora_fin")
        if fi and ff and ff < fi:
            self.add_error("fecha_fin", "Debe ser mayor o igual a la fecha de inicio.")
        if (hi and not hf) or (hf and not hi):
            raise forms.ValidationError("Si define una hora, debe indicar inicio y fin.")
        if hi and hf and hf <= hi:
            raise forms.ValidationError("La hora fin debe ser mayor que la hora inicio.")
        if data.get("aplicar_a") == "departamento" and not data.get("departamento"):
            self.add_error("departamento", "Indique el departamento.")
        return data
