from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.usuarios.urls')),
    path('api/aulas/', include('apps.aulas.urls')),
    path('api/planificacion/', include('apps.planificacion.urls')),
    path('api/asignaciones/', include('apps.asignaciones.urls')),
    path('api/reportes/', include('apps.reportes.urls')),
    path('api/bot/', include('apps.bot_telegram.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# apps/usuarios/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegistroUsuarioView.as_view(), name='registro'),
    path('login/', views.login_view, name='login'),
    path('perfil/', views.perfil_usuario_view, name='perfil'),
]

# apps/aulas/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.AulaListView.as_view(), name='lista-aulas'),
    path('tipos/', views.TipoAulaListView.as_view(), name='tipos-aula'),
    path('disponibilidad/', views.disponibilidad_aulas_view, name='disponibilidad-aulas'),
    path('buscar-docente/', views.buscar_docente_view, name='buscar-docente'),
]