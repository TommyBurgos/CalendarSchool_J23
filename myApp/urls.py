from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("panel/admin/", views.dashboard_admin, name="dashboard_admin"),  
    path("panel/admin/citas/<int:pk>/confirmar/", views.confirmar_cita_admin, name="confirmar_cita_admin"),
    path("panel/admin/citas/<int:pk>/cancelar/", views.cancelar_cita_admin, name="cancelar_cita_admin"),
    path("panel/admin/citas/<int:pk>/", views.cita_detalle_admin, name="cita_detalle_admin"),
    path("panel/admin/agenda/", views.agenda_global_admin, name="agenda_global_admin"),
]