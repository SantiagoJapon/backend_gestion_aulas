from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, Prefetch
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from .models import PlanificacionAcademica, Periodo, Carrera, Materia, FranjaHoraria
from .serializers import (
    PlanificacionAcademicaListSerializer,
    PlanificacionAcademicaDetailSerializer,
    PlanificacionAcademicaCreateSerializer,
    PlanificacionAcademicaUpdateSerializer,
    PeriodoSerializer,
    CarreraSerializer,
    MateriaSerializer,
    FranjaHorariaSerializer,
)
from apps.asignaciones.models import AsignacionDocente, HorarioClase, ConflictoHorario

User = get_user_model()


class PlanificacionAcademicaFilter(django_filters.FilterSet):
    """Filtros para planificaciones académicas"""
    estado = django_filters.ChoiceFilter(choices=PlanificacionAcademica.ESTADOS)
    periodo = django_filters.NumberFilter(field_name='periodo__id')
    carrera = django_filters.NumberFilter(field_name='carreras__id')
    creado_por = django_filters.NumberFilter(field_name='creado_por__id')
    fecha_inicio = django_filters.DateFilter(field_name='fecha_creacion', lookup_expr='gte')
    fecha_fin = django_filters.DateFilter(field_name='fecha_creacion', lookup_expr='lte')
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')

    class Meta:
        model = PlanificacionAcademica
        fields = ['estado', 'periodo', 'carrera', 'creado_por', 'fecha_inicio', 'fecha_fin', 'nombre']


class PlanificacionAcademicaViewSet(ModelViewSet):
    """
    ViewSet completo para gestionar planificaciones académicas
    """
    queryset = PlanificacionAcademica.objects.all().select_related(
        'periodo', 'creado_por', 'aprobado_por'
    ).prefetch_related('carreras')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PlanificacionAcademicaFilter
    search_fields = ['nombre', 'observaciones']
    ordering_fields = ['fecha_creacion', 'nombre', 'estado']
    ordering = ['-fecha_creacion']

    def get_serializer_class(self):
        """Retorna el serializer apropiado según la acción"""
        if self.action == 'list':
            return PlanificacionAcademicaListSerializer
        elif self.action == 'create':
            return PlanificacionAcademicaCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PlanificacionAcademicaUpdateSerializer
        return PlanificacionAcademicaDetailSerializer

    def get_queryset(self):
        """Personaliza el queryset según el usuario"""
        queryset = super().get_queryset()

        # Si no es admin, solo ver sus planificaciones o las aprobadas
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(creado_por=self.request.user) |
                Q(estado__in=['aprobada', 'vigente'])
            )

        return queryset

    def perform_create(self, serializer):
        """Asigna el usuario actual como creador"""
        serializer.save(creado_por=self.request.user)

    def perform_update(self, serializer):
        """Validaciones adicionales en actualización"""
        instance = self.get_object()

        # Solo el creador o admin puede editar
        if instance.creado_por != self.request.user and not self.request.user.is_staff:
            raise PermissionError("No tienes permisos para editar esta planificación")

        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cambiar_estado(self, request, pk=None):
        """
        Cambia el estado de una planificación
        """
        planificacion = self.get_object()
        nuevo_estado = request.data.get('estado')

        if nuevo_estado not in dict(PlanificacionAcademica.ESTADOS):
            return Response(
                {'error': 'Estado inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validaciones de transición de estado
        transiciones_validas = {
            'borrador': ['revision'],
            'revision': ['borrador', 'aprobada'],
            'aprobada': ['vigente'],
            'vigente': ['cerrada'],
            'cerrada': []
        }

        if nuevo_estado not in transiciones_validas.get(planificacion.estado, []):
            return Response(
                {'error': f'No se puede cambiar de {planificacion.get_estado_display()} a {dict(PlanificacionAcademica.ESTADOS)[nuevo_estado]}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Solo admin puede aprobar
        if nuevo_estado == 'aprobada' and not request.user.is_staff:
            return Response(
                {'error': 'Solo administradores pueden aprobar planificaciones'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Actualizar estado
        planificacion.estado = nuevo_estado
        if nuevo_estado == 'aprobada':
            planificacion.aprobado_por = request.user
            from django.utils import timezone
            planificacion.fecha_aprobacion = timezone.now()

        planificacion.save()

        return Response({
            'message': f'Estado cambiado a {planificacion.get_estado_display()}',
            'estado': planificacion.estado
        })

    @action(detail=True, methods=['get'])
    def estadisticas(self, request, pk=None):
        """
        Obtiene estadísticas detalladas de la planificación
        """
        planificacion = self.get_object()

        # Estadísticas básicas
        total_asignaciones = AsignacionDocente.objects.filter(
            planificacion=planificacion, is_activa=True
        ).count()

        total_horarios = HorarioClase.objects.filter(
            asignacion_docente__planificacion=planificacion,
            is_activa=True
        ).count()

        total_conflictos = ConflictoHorario.objects.filter(
            planificacion=planificacion,
            estado='pendiente'
        ).count()

        # Estadísticas por docente
        docentes_stats = AsignacionDocente.objects.filter(
            planificacion=planificacion,
            is_activa=True
        ).values(
            'docente__first_name',
            'docente__last_name'
        ).annotate(
            total_materias=Count('materia'),
            total_horas=Sum('carga_horaria_semanal')
        )

        # Utilización de aulas
        aulas_stats = HorarioClase.objects.filter(
            asignacion_docente__planificacion=planificacion,
            is_activa=True
        ).values(
            'aula__codigo',
            'aula__nombre'
        ).annotate(
            total_horarios=Count('id')
        )

        return Response({
            'resumen': {
                'total_asignaciones': total_asignaciones,
                'total_horarios': total_horarios,
                'total_conflictos': total_conflictos,
                'progreso': round((total_horarios / max(total_asignaciones, 1)) * 100, 1)
            },
            'docentes': list(docentes_stats),
            'aulas': list(aulas_stats),
        })

    @action(detail=True, methods=['get'])
    def validar(self, request, pk=None):
        """
        Valida la planificación detectando conflictos
        """
        planificacion = self.get_object()

        # Ejecutar validaciones
        conflictos = []

        # 1. Conflictos de horario por docente
        horarios = HorarioClase.objects.filter(
            asignacion_docente__planificacion=planificacion,
            is_activa=True
        ).select_related('asignacion_docente__docente', 'franja_horaria')

        docente_horarios = {}
        for horario in horarios:
            docente_id = horario.asignacion_docente.docente.id
            franja_key = (horario.franja_horaria.dia_semana, horario.franja_horaria.hora_inicio)

            if docente_id not in docente_horarios:
                docente_horarios[docente_id] = set()

            if franja_key in docente_horarios[docente_id]:
                conflictos.append({
                    'tipo': 'conflicto_docente',
                    'descripcion': f'Docente {horario.asignacion_docente.docente.get_full_name()} tiene clases simultáneas',
                    'severidad': 'alta'
                })

            docente_horarios[docente_id].add(franja_key)

        # 2. Conflictos de aula
        aula_horarios = {}
        for horario in horarios:
            aula_id = horario.aula.id
            franja_key = (horario.franja_horaria.dia_semana, horario.franja_horaria.hora_inicio)

            if aula_id not in aula_horarios:
                aula_horarios[aula_id] = set()

            if franja_key in aula_horarios[aula_id]:
                conflictos.append({
                    'tipo': 'conflicto_aula',
                    'descripcion': f'Aula {horario.aula.codigo} tiene clases simultáneas',
                    'severidad': 'alta'
                })

            aula_horarios[aula_id].add(franja_key)

        # 3. Validar capacidad
        for horario in horarios:
            if horario.capacidad_estudiantes and horario.capacidad_estudiantes > horario.aula.capacidad:
                conflictos.append({
                    'tipo': 'capacidad_excedida',
                    'descripcion': f'Capacidad de estudiantes ({horario.capacidad_estudiantes}) excede capacidad del aula {horario.aula.codigo} ({horario.aula.capacidad})',
                    'severidad': 'media'
                })

        return Response({
            'valida': len(conflictos) == 0,
            'total_conflictos': len(conflictos),
            'conflictos': conflictos,
            'mensaje': 'Planificación válida' if len(conflictos) == 0 else f'Se encontraron {len(conflictos)} conflictos'
        })

    @action(detail=True, methods=['post'])
    def duplicar(self, request, pk=None):
        """
        Duplica una planificación existente
        """
        planificacion_original = self.get_object()
        nuevo_nombre = request.data.get('nombre', f"Copia de {planificacion_original.nombre}")

        # Crear nueva planificación
        nueva_planificacion = PlanificacionAcademica.objects.create(
            nombre=nuevo_nombre,
            periodo=planificacion_original.periodo,
            observaciones=f"Copia de: {planificacion_original.nombre}",
            creado_por=request.user
        )

        # Copiar carreras
        nueva_planificacion.carreras.set(planificacion_original.carreras.all())

        # Copiar asignaciones
        for asignacion in planificacion_original.asignaciones_docente.filter(is_activa=True):
            AsignacionDocente.objects.create(
                planificacion=nueva_planificacion,
                docente=asignacion.docente,
                materia=asignacion.materia,
                carga_horaria_semanal=asignacion.carga_horaria_semanal,
                observaciones=f"Copiado de planificación #{planificacion_original.id}",
                is_activa=True
            )

        serializer = PlanificacionAcademicaDetailSerializer(nueva_planificacion)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# Vistas auxiliares para recursos relacionados

class PeriodoListView(generics.ListAPIView):
    """Lista todos los períodos académicos"""
    queryset = Periodo.objects.filter(is_activo=True).order_by('-anio', '-numero')
    serializer_class = PeriodoSerializer
    permission_classes = [IsAuthenticated]


class CarreraListView(generics.ListAPIView):
    """Lista todas las carreras activas"""
    queryset = Carrera.objects.all().order_by('nombre')
    serializer_class = CarreraSerializer
    permission_classes = [IsAuthenticated]


class MateriaListView(generics.ListAPIView):
    """Lista materias con filtros"""
    queryset = Materia.objects.filter(is_activa=True).select_related('carrera')
    serializer_class = MateriaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['carrera', 'semestre']
    search_fields = ['nombre', 'codigo']


class FranjaHorariaListView(generics.ListAPIView):
    """Lista franjas horarias disponibles"""
    queryset = FranjaHoraria.objects.all().order_by('dia_semana', 'hora_inicio')
    serializer_class = FranjaHorariaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['dia_semana']


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_resumen(request):
    """
    Endpoint para obtener resumen del dashboard
    """
    user = request.user

    # Filtrar según el rol del usuario
    if user.is_staff:
        planificaciones = PlanificacionAcademica.objects.all()
    else:
        planificaciones = PlanificacionAcademica.objects.filter(
            Q(creado_por=user) | Q(estado__in=['aprobada', 'vigente'])
        )

    # Estadísticas generales
    total_planificaciones = planificaciones.count()
    planificaciones_activas = planificaciones.filter(estado__in=['revision', 'aprobada', 'vigente']).count()

    # Estadísticas por estado
    estados_stats = {}
    for estado_key, estado_nombre in PlanificacionAcademica.ESTADOS:
        count = planificaciones.filter(estado=estado_key).count()
        estados_stats[estado_key] = {
            'nombre': estado_nombre,
            'count': count
        }

    # Planificaciones recientes
    planificaciones_recientes = planificaciones.order_by('-fecha_creacion')[:5]
    planificaciones_recientes_data = PlanificacionAcademicaListSerializer(
        planificaciones_recientes, many=True
    ).data

    return Response({
        'resumen': {
            'total_planificaciones': total_planificaciones,
            'planificaciones_activas': planificaciones_activas,
            'usuario_actual': user.get_full_name() or user.username,
            'rol': user.rol
        },
        'estados': estados_stats,
        'planificaciones_recientes': planificaciones_recientes_data
    })


# Endpoints para ejecución del algoritmo de planificación

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ejecutar_algoritmo(request, planificacion_id):
    """
    Ejecuta el algoritmo de asignación automática de horarios
    """
    try:
        planificacion = PlanificacionAcademica.objects.get(id=planificacion_id)
    except PlanificacionAcademica.DoesNotExist:
        return Response(
            {'error': 'Planificación no encontrada'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Validar permisos
    if planificacion.creado_por != request.user and not request.user.is_staff:
        return Response(
            {'error': 'No tienes permisos para ejecutar algoritmos en esta planificación'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Validar estado
    if planificacion.estado not in ['borrador', 'revision']:
        return Response(
            {'error': f'No se puede ejecutar el algoritmo en planificaciones con estado: {planificacion.get_estado_display()}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Parámetros del algoritmo
    strategy = request.data.get('strategy', 'docente_priority')
    save_results = request.data.get('save', False)
    dry_run = request.data.get('dry_run', True)

    # Parámetros específicos para algoritmo genético
    engine_params = {}
    if strategy == 'genetic_algorithm':
        engine_params['population_size'] = request.data.get('population_size', 50)
        engine_params['generations'] = request.data.get('generations', 100)

    try:
        # Importar y ejecutar algoritmo
        from .scheduling.base import SchedulingStrategy
        from .scheduling.strategies import SchedulingEngineFactory

        # Validar estrategia
        if strategy not in [s.value for s in SchedulingStrategy]:
            return Response(
                {'error': f'Estrategia inválida: {strategy}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear motor de planificación
        strategy_enum = SchedulingStrategy(strategy)
        engine = SchedulingEngineFactory.create_engine(strategy_enum, **engine_params)

        # Ejecutar planificación
        result = engine.execute_scheduling(planificacion)

        # Preparar respuesta
        response_data = {
            'success': result.success,
            'strategy_used': result.strategy_used.value,
            'execution_time': result.execution_time,
            'score': result.score,
            'message': result.message,
            'total_assignments': len(result.assignments),
            'total_conflicts': len(result.conflicts),
            'total_unassigned': len(result.unassigned),
            'dry_run': dry_run
        }

        # Agregar detalles si se solicitan
        if request.data.get('include_details', False):
            from .serializers import HorarioClaseSerializer, ConflictoHorarioSerializer, AsignacionDocenteSerializer

            # Convertir asignaciones a formato serializable
            assignments_data = []
            for assignment in result.assignments:
                assignments_data.append({
                    'docente': assignment.asignacion_docente.docente.get_full_name(),
                    'materia': assignment.asignacion_docente.materia.nombre,
                    'aula': assignment.aula.codigo,
                    'franja': f"{assignment.franja_horaria.get_dia_semana_display()} {assignment.franja_horaria.hora_inicio}-{assignment.franja_horaria.hora_fin}",
                    'score': assignment.score
                })

            response_data['assignments'] = assignments_data

            # Conflictos
            conflicts_data = []
            for conflict in result.conflicts:
                conflicts_data.append({
                    'tipo': conflict.tipo,
                    'descripcion': conflict.descripcion
                })
            response_data['conflicts'] = conflicts_data

            # No asignadas
            unassigned_data = []
            for unassigned in result.unassigned:
                unassigned_data.append({
                    'docente': unassigned.docente.get_full_name(),
                    'materia': unassigned.materia.nombre,
                    'horas_semanales': unassigned.carga_horaria_semanal
                })
            response_data['unassigned'] = unassigned_data

        # Guardar resultados si se especifica y no es dry-run
        if save_results and not dry_run:
            saved = engine.save_scheduling_result(planificacion, result)
            response_data['saved'] = saved

            if saved and result.success:
                # Actualizar estado de planificación
                if planificacion.estado == 'borrador':
                    planificacion.estado = 'revision'
                    planificacion.save()
                    response_data['estado_actualizado'] = 'revision'

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': f'Error ejecutando algoritmo: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def estrategias_disponibles(request):
    """
    Lista las estrategias de planificación disponibles
    """
    try:
        from .scheduling.strategies import SchedulingEngineFactory
        estrategias = SchedulingEngineFactory.get_available_strategies()
        return Response({'estrategias': estrategias})
    except ImportError:
        return Response({
            'estrategias': [
                {
                    'key': 'docente_priority',
                    'name': 'Prioridad Docente',
                    'description': 'Prioriza las preferencias de los docentes'
                },
                {
                    'key': 'aula_optimization',
                    'name': 'Optimización de Aulas',
                    'description': 'Optimiza el uso de las aulas disponibles'
                },
                {
                    'key': 'balanced_distribution',
                    'name': 'Distribución Equilibrada',
                    'description': 'Distribuye las clases de manera equilibrada'
                },
                {
                    'key': 'genetic_algorithm',
                    'name': 'Algoritmo Genético',
                    'description': 'Usa algoritmo genético para optimización avanzada'
                }
            ]
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def estado_algoritmo(request, planificacion_id):
    """
    Verifica el estado actual del algoritmo para una planificación
    (Para futuras implementaciones con tareas asíncronas)
    """
    try:
        planificacion = PlanificacionAcademica.objects.get(id=planificacion_id)
    except PlanificacionAcademica.DoesNotExist:
        return Response(
            {'error': 'Planificación no encontrada'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Por ahora, el algoritmo es síncrono, pero esta estructura permite
    # futuras implementaciones asíncronas con Celery

    return Response({
        'planificacion_id': planificacion_id,
        'estado': 'completado',  # ready, running, completed, failed
        'puede_ejecutar': planificacion.estado in ['borrador', 'revision'],
        'ultima_ejecucion': None,  # Timestamp de última ejecución
        'asignaciones_actuales': HorarioClase.objects.filter(
            asignacion_docente__planificacion=planificacion,
            is_activa=True
        ).count()
    })