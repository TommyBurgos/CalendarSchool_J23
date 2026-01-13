from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
    
class Institucion(models.Model):
    nombre = models.CharField(max_length=255)
    codigo = models.CharField(max_length=50, unique=True)   # Ej: UEDSM-01
    logo = models.ImageField(upload_to="instituciones/", null=True, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    zona_horaria = models.CharField(max_length=100, default="America/Guayaquil")

    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class User(AbstractUser):
    cedula = models.CharField(
        max_length=20, unique=True, null=True, blank=True,
        validators=[RegexValidator(r"^\d{8,20}$", "Cédula inválida (8–20 dígitos).")]
    )
    institucion = models.ForeignKey(
        Institucion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="usuarios"
    )
    email = models.EmailField(unique=True, null=True, blank=True)
    imgPerfil = models.ImageField(upload_to="users/", default="imageDefault.png")
    debe_cambiar_password = models.BooleanField(default=True)
    rol = models.ForeignKey("user.Rol", null=True, blank=True, on_delete=models.SET_NULL, related_name="usuarios")
    telefono = models.CharField(
    max_length=20,
    null=True,
    blank=True,
    help_text="Número de celular en formato internacional, ej: +593987654321",
    validators=[
        RegexValidator(
            r"^\+?\d{7,20}$",
            "Número de teléfono inválido (use solo dígitos y opcional + al inicio)."
        )
    ]
)


    def save(self, *args, **kwargs):
        # Normaliza
        if self.email:
            self.email = self.email.strip().lower()
        if self.cedula:
            self.cedula = self.cedula.strip()
            # **Regla nueva**: autenticación por cédula = username
            self.username = self.cedula
        super().save(*args, **kwargs)

class UserInstitucion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    institucion = models.ForeignKey("user.Institucion", on_delete=models.CASCADE, null=True, blank=True)
    rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, null=True, blank=True)

    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "institucion")
