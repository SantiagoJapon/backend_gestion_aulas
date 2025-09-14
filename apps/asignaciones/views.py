from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from .models import AsignacionDocente, HorarioClase, ConflictoHorario, RegistroAsistencia
from .serializers import (
    AsignacionDocenteSerializer,
    HorarioClaseSerializer,
    HorarioClaseCreateSerializer,
    ConflictoHorarioSerializer,
    RegistroAsistenciaSerializer
)
from apps.planificacion.models import PlanificacionAcademica


class HorarioClaseFilter(django_filters.FilterSet):
    """Filtros para horarios de clase"""
    planificacion = django_filters.NumberFilter(field_name='asignacion_docente__planificacion__id')
    docente = django_filters.NumberFilter(field_name='asignacion_docente__docente__id')
    materia = django_filters.NumberFilter(field_name='asignacion_docente__materia__id')
    aula = django_filters.NumberFilter(field_name='aula__id')
    dia_semana = django_filters.CharFilter(field_name='franja_horaria__dia_semana')
    modalidad = django_filters.ChoiceFilter(choices=HorarioClase.MODALIDADES)

    class Meta:
        model = HorarioClase
        fields = ['planificacion', 'docente', 'materia', 'aula', 'dia_semana', 'modalidad']


class HorarioClaseViewSet(ModelViewSet):
    """
    ViewSet para gestión completa de horarios de clase
    """
    queryset = HorarioClase.objects.all().select_related(
        'asignacion_docente__docente',
        'asignacion_docente__materia',
        'asignacion_docente__planificacion',
        'franja_horaria',
        'aula'
    ).filter(is_activa=True)
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = HorarioClaseFilter
    search_fields = ['asignacion_docente__materia__nombre', 'aula__codigo', 'observaciones']
    ordering_fields = ['fecha_creacion', 'franja_horaria__dia_semana', 'franja_horaria__hora_inicio']
    ordering = ['franja_horaria__dia_semana', 'franja_horaria__hora_inicio']

    def get_serializer_class(self):
        """Retorna el serializer apropiado según la acción"""
        if self.action in ['create', 'update', 'partial_update']:
            return HorarioClaseCreateSerializer
        return HorarioClaseSerializer

    def get_queryset(self):
        """Personaliza el queryset según el usuario"""
        queryset = super().get_queryset()

        # Si no es admin, solo ver horarios de sus planificaciones o aprobadas
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(asignacion_docente__planificacion__creado_por=self.request.user) |
                Q(asignacion_docente__planificacion__estado__in=['aprobada', 'vigente'])
            )

        return queryset

    def perform_create(self, serializer):
        """Validaciones adicionales en creación"""
        serializer.save()

    def perform_update(self, serializer):
        """Validaciones adicionales en actualización"""
        instance = self.get_object()

        # Solo el creador de la planificación o admin puede editar
        if (instance.asignacion_docente.planificacion.creado_por != self.request.user and
            not self.request.user.is_staff):
            raise PermissionError("No tienes permisos para editar este horario")

        # No permitir editar horarios de planificaciones aprobadas/vigentes
        if instance.asignacion_docente.planificacion.estado in ['vigente', 'cerrada']:
            raise PermissionError("No se pueden editar horarios de planificaciones vigentes o cerradas")

        serializer.save()

    @action(detail=False, methods=['get'])
    def por_planificacion(self, request):
        """
        Obtiene todos los horarios de una planificación específica
        """
        planificacion_id = request.query_params.get('planificacion_id')
        if not planificacion_id:
            return Response(
                {'error': 'Parámetro planificacion_id requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            planificacion = PlanificacionAcademica.objects.get(id=planificacion_id)
        except PlanificacionAcademica.DoesNotExist:
            return Response(
                {'error': 'Planificación no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )

        horarios = self.get_queryset().filter(
            asignacion_docente__planificacion=planificacion
        )

        # Agrupar por día de la semana
        horarios_por_dia = {}
        for horario in horarios:
            dia = horario.franja_horaria.get_dia_semana_display()
            if dia not in horarios_por_dia:
                horarios_por_dia[dia] = []
            horarios_por_dia[dia].append(HorarioClaseSerializer(horario).data)

        return Response({
            'planificacion_id': planificacion_id,
            'planificacion_nombre': planificacion.nombre,
            'total_horarios': horarios.count(),
            'horarios_por_dia': horarios_por_dia
        })

    @action(detail=False, methods=['get'])
    def matriz_horarios(self, request):
        """
        Genera una matriz de horarios (vista tabla) para una planificación
        """
        planificacion_id = request.query_params.get('planificacion_id')
        if not planificacion_id:
            return Response(
                {'error': 'Parámetro planificacion_id requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        horarios = self.get_queryset().filter(
            asignacion_docente__planificacion=planificacion_id
        )

        # Obtener todas las franjas horarias únicas
        franjas = set()
        for horario in horarios:
            franjas.add((
                horario.franja_horaria.hora_inicio,
                horario.franja_horaria.hora_fin
            ))
        franjas_ordenadas = sorted(list(franjas))

        # Crear matriz
        dias_semana = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado']
        matriz = {}

        for dia in dias_semana:
            matriz[dia] = {}
            for hora_inicio, hora_fin in franjas_ordenadas:
                franja_key = f"{hora_inicio}-{hora_fin}"
                matriz[dia][franja_key] = []

                # Buscar horarios para este día y franja
                horarios_franja = horarios.filter(
                    franja_horaria__dia_semana=dia,
                    franja_horaria__hora_inicio=hora_inicio,
                    franja_horaria__hora_fin=hora_fin
                )

                for horario in horarios_franja:
                    matriz[dia][franja_key].append({
                        'id': horario.id,
                        'materia': horario.asignacion_docente.materia.nombre,
                        'docente': horario.asignacion_docente.docente.get_full_name(),
                        'aula': horario.aula.codigo,
                        'modalidad': horario.modalidad,
                        'estudiantes': horario.capacidad_estudiantes
                    })

        return Response({
            'planificacion_id': planificacion_id,
            'franjas_horarias': [f"{inicio}-{fin}" for inicio, fin in franjas_ordenadas],
            'matriz': matriz
        })


class ConflictoHorarioViewSet(ModelViewSet):
    """
    ViewSet para gestión de conflictos de horario
    """
    queryset = ConflictoHorario.objects.all().select_related('planificacion')
    serializer_class = ConflictoHorarioSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['planificacion', 'tipo', 'estado']
    ordering = ['-fecha_deteccion']

    def get_queryset(self):
        """Personaliza el queryset según el usuario"""
        queryset = super().get_queryset()

        # Si no es admin, solo ver conflictos de sus planificaciones
        if not self.request.user.is_staff:
            queryset = queryset.filter(planificacion__creado_por=self.request.user)

        return queryset

    @action(detail=True, methods=['post'])
    def marcar_resuelto(self, request, pk=None):
        """
        Marca un conflicto como resuelto
        """
        conflicto = self.get_object()

        if conflicto.estado == 'resuelto':
            return Response(
                {'message': 'El conflicto ya estaba marcado como resuelto'},
                status=status.HTTP_200_OK
            )

        conflicto.estado = 'resuelto'
        from django.utils import timezone
        conflicto.fecha_resolucion = timezone.now()
        conflicto.save()

        return Response({
            'message': 'Conflicto marcado como resuelto',
            'fecha_resolucion': conflicto.fecha_resolucion
        })

    @action(detail=False, methods=['post'])
    def detectar_conflictos(self, request):
        """
        Detecta conflictos en una planificación específica
        """
        planificacion_id = request.data.get('planificacion_id')
        if not planificacion_id:
            return Response(
                {'error': 'Parámetro planificacion_id requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            planificacion = PlanificacionAcademica.objects.get(id=planificacion_id)
        except PlanificacionAcademica.DoesNotExist:
            return Response(
                {'error': 'Planificación no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Lógica de detección de conflictos
        conflictos_detectados = []
        horarios = HorarioClase.objects.filter(
            asignacion_docente__planificacion=planificacion,
            is_activa=True
        )

        # 1. Conflictos de docente (mismo docente, misma franja)
        docente_conflictos = {}
        for horario in horarios:
            key = (horario.asignacion_docente.docente.id,
                   horario.franja_horaria.dia_semana,
                   horario.franja_horaria.hora_inicio)

            if key in docente_conflictos:
                conflictos_detectados.append({
                    'tipo': 'conflicto_docente',
                    'descripcion': f'Docente {horario.asignacion_docente.docente.get_full_name()} tiene clases simultáneas',
                    'horarios_involucrados': [docente_conflictos[key].id, horario.id]
                })
            else:
                docente_conflictos[key] = horario

        # 2. Conflictos de aula (misma aula, misma franja)
        aula_conflictos = {}
        for horario in horarios:
            key = (horario.aula.id,
                   horario.franja_horaria.dia_semana,
                   horario.franja_horaria.hora_inicio)

            if key in aula_conflictos:
                conflictos_detectados.append({
                    'tipo': 'conflicto_aula',
                    'descripcion': f'Aula {horario.aula.codigo} tiene clases simultáneas',
                    'horarios_involucrados': [aula_conflictos[key].id, horario.id]
                })
            else:
                aula_conflictos[key] = horario

        # Guardar conflictos nuevos en la base de datos
        conflictos_guardados = 0
        for conflicto_data in conflictos_detectados:
            # Evitar duplicados
            if not ConflictoHorario.objects.filter(
                planificacion=planificacion,
                tipo=conflicto_data['tipo'],
                descripcion=conflicto_data['descripcion'],
                estado='pendiente'
            ).exists():
                ConflictoHorario.objects.create(
                    planificacion=planificacion,
                    tipo=conflicto_data['tipo'],
                    descripcion=conflicto_data['descripcion']
                )
                conflictos_guardados += 1

        return Response({
            'planificacion_id': planificacion_id,
            'conflictos_detectados': len(conflictos_detectados),
            'conflictos_nuevos': conflictos_guardados,
            'conflictos': conflictos_detectados
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resumen_horarios(request):
    """
    Endpoint para obtener resumen general de horarios
    """
    user = request.user

    # Filtrar según permisos del usuario
    if user.is_staff:
        horarios = HorarioClase.objects.filter(is_activa=True)
    else:
        horarios = HorarioClase.objects.filter(
            Q(asignacion_docente__planificacion__creado_por=user) |
            Q(asignacion_docente__planificacion__estado__in=['aprobada', 'vigente']),
            is_activa=True
        )

    # Estadísticas básicas
    total_horarios = horarios.count()
    planificaciones_con_horarios = horarios.values('asignacion_docente__planificacion').distinct().count()

    # Horarios por día
    horarios_por_dia = {}
    for dia_key, dia_nombre in [
        ('lunes', 'Lunes'), ('martes', 'Martes'), ('miercoles', 'Miércoles'),
        ('jueves', 'Jueves'), ('viernes', 'Viernes'), ('sabado', 'Sábado')
    ]:
        count = horarios.filter(franja_horaria__dia_semana=dia_key).count()
        horarios_por_dia[dia_nombre] = count

    # Aulas más utilizadas
    aulas_stats = horarios.values('aula__codigo', 'aula__nombre').annotate(
        total_horarios=Count('id')
    ).order_by('-total_horarios')[:5]

    # Docentes con más carga
    docentes_stats = horarios.values(
        'asignacion_docente__docente__first_name',
        'asignacion_docente__docente__last_name'
    ).annotate(
        total_horarios=Count('id')
    ).order_by('-total_horarios')[:5]

    return Response({
        'resumen': {
            'total_horarios': total_horarios,
            'planificaciones_con_horarios': planificaciones_con_horarios,
            'usuario_actual': user.get_full_name() or user.username
        },
        'distribucion': {
            'horarios_por_dia': horarios_por_dia,
            'aulas_mas_utilizadas': list(aulas_stats),
            'docentes_con_mas_carga': list(docentes_stats)
        }
    })