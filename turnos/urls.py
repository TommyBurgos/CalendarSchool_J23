from . import views
from django.urls import path
from . import views_admin, views_slots, views_docente, views_representante, views_coordinador


urlpatterns = [
    path("panel/admin/estudiantes/cargar/", views_admin.cargar_estudiantes, name="cargar_estudiantes"),
    path("panel/admin/estudiantes/formato/", views_admin.descargar_formato_estudiantes, name="formato_estudiantes"),
    path("panel/admin/docentes/", views_admin.listar_docentes, name="listar_docentes"),
    path("panel/admin/docentes/<int:user_id>/editar/", views_admin.editar_perfil_docente, name="editar_perfil_docente"),
    path("panel/admin/docentes/<int:docente_id>/disponibilidad/", views_admin.gestionar_disponibilidad_docente, name="gestionar_disponibilidad_docente"),
    path("panel/admin/docentes/disponibilidad/<int:disp_id>/eliminar/", views_admin.eliminar_disponibilidad, name="eliminar_disponibilidad"),
    path("panel/admin/docentes/excepcion/<int:exc_id>/eliminar/", views_admin.eliminar_excepcion, name="eliminar_excepcion"),
    path("panel/admin/docentes/cargar/", views_admin.cargar_docentes, name="cargar_docentes"),
    path("panel/admin/docentes/formato/", views_admin.formato_docentes, name="formato_docentes"),
    path("slots/", views_slots.api_slots, name="api_slots"),
    path("panel/admin/bloqueos/", views_admin.bloqueo_masivo, name="bloqueo_masivo"),

    #COORDINADOR.    
    # Descarga CSV usando ?export=1 (no necesita ruta extra)
    path("panel/coordinador/hoy/", views_coordinador.resumen_hoy, name="resumen_hoy"),
    path("panel/coordinador/semana/", views_coordinador.resumen_semana, name="resumen_semana"),
  

    #DOCENTE
    path("docente/", views_docente.dashboard_docente, name="dashboard_docente"),
    path("docente/disponibilidad/", views_docente.disponibilidad_list, name="disp_list"),
    path("docente/disponibilidad/nuevo/", views_docente.disponibilidad_create, name="disp_create"),
    path("docente/disponibilidad/<int:pk>/eliminar/", views_docente.disponibilidad_delete, name="disp_delete"),

    path("docente/excepciones/", views_docente.excepciones_list, name="exc_list"),
    path("docente/excepciones/nuevo/", views_docente.excepciones_create, name="exc_create"),
    path("docente/excepciones/<int:pk>/eliminar/", views_docente.excepciones_delete, name="exc_delete"),

    path("docente/agenda/dia/", views_docente.agenda_dia, name="agenda_dia"),
    path("docente/agenda/semana/", views_docente.agenda_semana, name="agenda_semana"),
    # turnos/urls.py
    path("docente/cita/<int:pk>/confirmar/", views_docente.cita_confirmar, name="cita_confirmar"),
    path("docente/cita/<int:pk>/cancelar/", views_docente.cita_cancelar, name="cita_cancelar"),

    # --- Representante ---
    path("representante/buscar/", views_representante.rep_buscar_slots, name="rep_buscar"),
    path("representante/reservar/", views_representante.rep_reservar_cita, name="rep_reservar"),
    path("representante/mis-citas/", views_representante.rep_mis_citas, name="rep_mis_citas"),
    path("representante/cita/<int:pk>/cancelar/", views_representante.rep_cita_cancelar, name="rep_cita_cancelar"),
    path("representante/buscar-semana/", views_representante.rep_buscar_semana, name="rep_buscar_semana"),





]
