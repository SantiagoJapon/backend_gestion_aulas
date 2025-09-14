from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/aulas/', include('apps.aulas.urls')),
    path('api/bot/', include('apps.bot_telegram.urls')),
    path('api/reportes/', include('apps.reportes.urls')),
    # APIs principales
    path('api/planificacion/', include('apps.planificacion.urls')),
    # path('api/auth/', include('apps.usuarios.urls')),
    # path('api/asignaciones/', include('apps.asignaciones.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)