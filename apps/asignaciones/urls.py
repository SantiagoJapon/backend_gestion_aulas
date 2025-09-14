from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router para ViewSets
router = DefaultRouter()
router.register(r'horarios', views.HorarioClaseViewSet, basename='horarios')
router.register(r'conflictos', views.ConflictoHorarioViewSet, basename='conflictos')

urlpatterns = [
    # ViewSet routes (incluye CRUD + acciones personalizadas)
    path('', include(router.urls)),

    # Endpoints adicionales
    path('resumen/', views.resumen_horarios, name='resumen-horarios'),
]

# Las URLs generadas automáticamente por los ViewSets serán:
#
# Horarios:
# GET    /horarios/                           -> Listar horarios
# POST   /horarios/                           -> Crear horario
# GET    /horarios/{id}/                      -> Detalle horario
# PUT    /horarios/{id}/                      -> Actualizar horario completa
# PATCH  /horarios/{id}/                      -> Actualizar horario parcial
# DELETE /horarios/{id}/                      -> Eliminar horario
# GET    /horarios/por_planificacion/         -> Horarios por planificación
# GET    /horarios/matriz_horarios/           -> Matriz de horarios
#
# Conflictos:
# GET    /conflictos/                         -> Listar conflictos
# POST   /conflictos/                         -> Crear conflicto
# GET    /conflictos/{id}/                    -> Detalle conflicto
# PUT    /conflictos/{id}/                    -> Actualizar conflicto
# PATCH  /conflictos/{id}/                    -> Actualizar conflicto parcial
# DELETE /conflictos/{id}/                    -> Eliminar conflicto
# POST   /conflictos/{id}/marcar_resuelto/    -> Marcar conflicto como resuelto
# POST   /conflictos/detectar_conflictos/     -> Detectar conflictos en planificación