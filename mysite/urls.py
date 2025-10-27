from django.contrib import admin
from django.urls import path,include
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('myApp.urls')),
    path("turnos/", include("turnos.urls")),
    path('usuarios/', include('user.urls')),
]

from myApp.views import exportar_citas_csv
urlpatterns += [
    path("panel/admin/citas/exportar/", exportar_citas_csv, name="exportar_citas_csv"),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root= settings.MEDIA_ROOT) 
