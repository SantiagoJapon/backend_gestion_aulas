from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router para ViewSets
router = DefaultRouter()
router.register(r'planificaciones', views.PlanificacionAcademicaViewSet, basename='planificaciones')

urlpatterns = [
    # ViewSet routes (incluye CRUD + acciones personalizadas)
    path('', include(router.urls)),

    # Endpoints auxiliares
    path('periodos/', views.PeriodoListView.as_view(), name='periodos-list'),
    path('carreras/', views.CarreraListView.as_view(), name='carreras-list'),
    path('materias/', views.MateriaListView.as_view(), name='materias-list'),
    path('franjas-horarias/', views.FranjaHorariaListView.as_view(), name='franjas-horarias-list'),

    # Dashboard
    path('dashboard/resumen/', views.dashboard_resumen, name='dashboard-resumen'),

    # Algoritmos de planificación
    path('algoritmo/estrategias/', views.estrategias_disponibles, name='algoritmo-estrategias'),
    path('algoritmo/<int:planificacion_id>/ejecutar/', views.ejecutar_algoritmo, name='algoritmo-ejecutar'),
    path('algoritmo/<int:planificacion_id>/estado/', views.estado_algoritmo, name='algoritmo-estado'),
]

# Las URLs generadas automáticamente por el ViewSet serán:
# GET    /planificaciones/                    -> Listar planificaciones
# POST   /planificaciones/                    -> Crear planificación
# GET    /planificaciones/{id}/               -> Detalle planificación
# PUT    /planificaciones/{id}/               -> Actualizar planificación completa
# PATCH  /planificaciones/{id}/               -> Actualizar planificación parcial
# DELETE /planificaciones/{id}/               -> Eliminar planificación
#
# Acciones personalizadas:
# POST   /planificaciones/{id}/cambiar_estado/     -> Cambiar estado
# GET    /planificaciones/{id}/estadisticas/       -> Obtener estadísticas
# GET    /planificaciones/{id}/validar/            -> Validar planificación
# POST   /planificaciones/{id}/duplicar/           -> Duplicar planificación