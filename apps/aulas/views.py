from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, time
from .models import Aula, TipoAula
from .serializers import AulaSerializer, TipoAulaSerializer, AulaDisponibilidadSerializer
from apps.asignaciones.models import AsignacionAula

class AulaListView(generics.ListAPIView):
    queryset = Aula.objects.all()
    serializer_class = AulaSerializer
    permission_classes = [IsAuthenticated]

class TipoAulaListView(generics.ListAPIView):
    queryset = TipoAula.objects.all()
    serializer_class = TipoAulaSerializer
    permission_classes = [IsAuthenticated]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def disponibilidad_aulas_view(request):
    """Vista para consultar disponibilidad de aulas en tiempo real"""
    fecha = request.GET.get('fecha', timezone.now().date())
    hora_actual = request.GET.get('hora', timezone.now().time())
    
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
    if isinstance(hora_actual, str):
        hora_actual = datetime.strptime(hora_actual, '%H:%M').time()
    
    aulas = Aula.objects.filter(is_disponible=True)
    resultado = []
    
    for aula in aulas:
        # Buscar asignaciones para esta aula en la fecha y hora especificadas
        asignaciones_hoy = AsignacionAula.objects.filter(
            aula=aula,
            clase_planificada__dia_semana=fecha.strftime('%A').lower(),
            estado='confirmada'
        )
        
        disponible = True
        proxima_clase = None
        ocupado_hasta = None
        
        for asignacion in asignaciones_hoy:
            clase = asignacion.clase_planificada
            if clase.hora_inicio <= hora_actual <= clase.hora_fin:
                disponible = False
                ocupado_hasta = clase.hora_fin
                break
            elif clase.hora_inicio > hora_actual:
                if not proxima_clase or clase.hora_inicio < datetime.strptime(proxima_clase, '%H:%M').time():
                    proxima_clase = clase.hora_inicio.strftime('%H:%M')
        
        data = {
            'aula': aula,
            'disponible': disponible,
            'proxima_clase': proxima_clase,
            'ocupado_hasta': ocupado_hasta
        }
        resultado.append(data)
    
    serializer = AulaDisponibilidadSerializer(resultado, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buscar_docente_view(request):
    """Vista para buscar la ubicación actual de un docente"""
    docente_nombre = request.GET.get('docente', '')
    fecha = request.GET.get('fecha', timezone.now().date())
    hora_actual = request.GET.get('hora', timezone.now().time())
    
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
    if isinstance(hora_actual, str):
        hora_actual = datetime.strptime(hora_actual, '%H:%M').time()
    
    # Buscar asignaciones del docente en el horario actual
    asignaciones = AsignacionAula.objects.filter(
        clase_planificada__docente__first_name__icontains=docente_nombre,
        clase_planificada__dia_semana=fecha.strftime('%A').lower(),
        clase_planificada__hora_inicio__lte=hora_actual,
        clase_planificada__hora_fin__gte=hora_actual,
        estado='confirmada'
    ).select_related('aula', 'clase_planificada__materia', 'clase_planificada__docente')
    
    if asignaciones.exists():
        asignacion = asignaciones.first()
        return Response({
            'encontrado': True,
            'docente': asignacion.clase_planificada.docente.get_full_name(),
            'aula': asignacion.aula.codigo,
            'aula_nombre': asignacion.aula.nombre,
            'materia': asignacion.clase_planificada.materia.nombre,
            'hora_inicio': asignacion.clase_planificada.hora_inicio,
            'hora_fin': asignacion.clase_planificada.hora_fin,
            'edificio': asignacion.aula.edificio,
            'piso': asignacion.aula.piso
        })
    
    return Response({
        'encontrado': False,
        'mensaje': f'El docente {docente_nombre} no tiene clases programadas en este momento'
    })