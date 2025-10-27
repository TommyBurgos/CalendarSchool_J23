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

class User(AbstractUser):
    cedula = models.CharField(
        max_length=20, unique=True, null=True, blank=True,
        validators=[RegexValidator(r"^\d{8,20}$", "Cédula inválida (8–20 dígitos).")]
    )
    email = models.EmailField(unique=True, null=True, blank=True)
    imgPerfil = models.ImageField(upload_to="users/", default="imageDefault.png")
    rol = models.ForeignKey("user.Rol", null=True, blank=True, on_delete=models.SET_NULL, related_name="usuarios")

    def save(self, *args, **kwargs):
        # Normaliza
        if self.email:
            self.email = self.email.strip().lower()
        if self.cedula:
            self.cedula = self.cedula.strip()
            # **Regla nueva**: autenticación por cédula = username
            self.username = self.cedula
        super().save(*args, **kwargs)

