# CalendarSchool — Estado del Proyecto (MVP)

## Resumen
Plataforma Django para gestionar turnos escolares (citas) entre Representantes y Docentes, con panel de Administración.  
Zona horaria: **America/Guayaquil** · Idioma: **es-EC** · Django **4.2.x**.

---

## Apps y responsabilidades
- **user/**
  - `User` (username = **cédula**), `Rol`
  - Formularios de perfil (`PerfilUsuarioForm`)
  - Vistas: login/registro, **mi_perfil**
  - Decorador: `@requiere_rol("...")`
- **turnos/**
  - Modelos: `PerfilDocente`, `DisponibilidadSemanal`, `ExcepcionDisponibilidad`, `Cita`, `Estudiante`, `RelacionRepresentacion`, `FeriadoInstitucional`
  - Formularios: filtros de citas, carga CSV (estudiantes/docentes), perfil/docente, disponibilidad/excepciones, bloqueo masivo
  - Servicios: **`generar_slots(docente, fecha)`**
  - Vistas admin: dashboard, listar/editar docentes, gestionar disponibilidad, carga CSV (estudiantes/docentes), bloqueo masivo, exportar CSV
  - API: `GET /turnos/slots/?docente_id=ID&fecha=YYYY-MM-DD` → slots libres (JSON)
  - Commands: `importar_estudiantes`, `importar_docentes`

---

## Funcionalidad ADMIN (MVP)
- Dashboard con métricas, filtros y **acciones rápidas** (confirmar/cancelar).
- **Reportes CSV** con filtros activos (inicio, fin, estado, docente, representante, alumno, curso, motivo).
- **Carga CSV Estudiantes** (con `representante_cedula`/`representante_email`):
  - Crea/actualiza `Estudiante` y `RelacionRepresentacion`.
  - Crea usuario representante (pass: `12345678`) y **asigna rol Representante** si no lo tiene.
- **Carga CSV Docentes** (username=cédula):
  - Crea/actualiza usuario + `PerfilDocente` (bloque, max por día, depto, tel).
  - **Disponibilidad opcional** (ej: `LUN 08:00-10:00|MAR 09:00-11:00`), con `reemplazar_disponibilidad`.
- **Bloqueo masivo** (feriados/eventos): por rango de fechas (día completo u horas), a todos o por departamento.
- **Mi Perfil**: ver/editar datos del usuario e imagen; cédula solo lectura.

---

## Modelos clave (resumen)
- `User(cedula unique, email optional, rol FK)` → username = cédula.
- `PerfilDocente(usuario, minutos_por_bloque, maximo_citas_diarias, activo, depto, tel)`.
- `DisponibilidadSemanal(docente, dia_semana, hora_inicio, hora_fin)`.
- `ExcepcionDisponibilidad(docente, fecha, hora_inicio, hora_fin, tipo=BLOQUEO/EXTRA)`.
- `Cita(docente, representante, inicio, fin, estado, curso_estudiante, nombre_estudiante, estudiante FK opcional)`  
  - Validaciones: no pasado, **24h de antelación**, sin solapes, alineado a bloque.
- `Estudiante(cedula unique, nombre, curso)` y `RelacionRepresentacion(estudiante, representante, parentesco, verificado, fuente, activo)`.
- `FeriadoInstitucional(nombre, fecha_inicio/fin, hora opcional)`.

---

## Endpoints y rutas (principales)
- Panel Admin:
  - `/panel/admin/` → `dashboard_admin`
  - `/panel/admin/citas/exportar/` → `exportar_citas_csv`
  - `/panel/admin/estudiantes/cargar/` (+ formato)
  - `/panel/admin/docentes/cargar/` (+ formato)
  - `/panel/admin/docentes/` (listar) → editar perfil / disponibilidad
  - `/panel/admin/bloqueos/` → bloqueo masivo
- API Slots:
  - `/turnos/slots/?docente_id=ID&fecha=YYYY-MM-DD`
- Perfil:
  - `/mi-perfil/`

---

## CSV — Formatos
**Estudiantes**

---

## Pendientes inmediatos (sugerido)
1. **Módulo Docente**: “Mi Agenda” (día/semana), confirmar/cancelar propias citas, editar disponibilidad.
2. **Buscador de slots (UI)** para Representante y flujo de reserva.
3. (Opcional) Configuración global (`ParametroSistema`) y bitácora (`LogAccion`).
4. (Futuro) Generalizar a **Recurso** (DECE/Rectorado) sin romper MVP.

---

## Convenciones
- Nombres y texto en **es-EC**.
- Relacionar modelos con `settings.AUTH_USER_MODEL`.
- Validaciones en `clean()` + servicios (reservas).
- Mensajes de Django habilitados.
- `USE_TZ=True`, TZ: **America/Guayaquil**.

## Notas de seguridad
- Password por defecto importaciones: **12345678** (forzar cambio en producción).
- Cédula = username: evita cambios directos desde UI (solo admin).
- No exponer endpoints de importación sin rol **Administrador**.
