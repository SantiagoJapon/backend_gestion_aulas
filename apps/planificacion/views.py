from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import pandas as pd
from .models import PlanificacionAcademica, ClasePlanificada, PeriodoAcademico
from .serializers import PlanificacionAcademicaSerializer, ClasePlanificadaSerializer
from .tasks import procesar_planificacion_task

class PlanificacionListCreateView(generics.ListCreateAPIView):
    serializer_class = PlanificacionAcademicaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.rol == 'director':
            return PlanificacionAcademica.objects.filter(director=user)
        elif user.rol in ['administrador']:
            return PlanificacionAcademica.objects.all()
        return PlanificacionAcademica.objects.none()
    
    def perform_create(self, serializer):
        if self.request.user.rol == 'director':
            planificacion = serializer.save(director=self.request.user)
            # Procesar archivo de planificación de forma asíncrona
            procesar_planificacion_task.delay(planificacion.id)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cargar_planificacion_excel_view(request):
    """Vista para procesar archivo Excel de planificación"""
    if request.user.rol != 'director':
        return Response({'error': 'Solo los directores pueden cargar planificaciones'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    archivo = request.FILES.get('archivo')
    periodo_id = request.data.get('periodo_id')
    carrera = request.data.get('carrera')
    
    if not archivo or not periodo_id or not carrera:
        return Response({'error': 'Faltan datos requeridos'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Crear registro de planificación
        periodo = get_object_or_404(PeriodoAcademico, id=periodo_id)
        planificacion = PlanificacionAcademica.objects.create(
            periodo=periodo,
            director=request.user,
            carrera=carrera,
            archivo_planificacion=archivo
        )
        
        # Procesar archivo de forma asíncrona
        procesar_planificacion_task.delay(planificacion.id)
        
        return Response({
            'message': 'Planificación cargada exitosamente. Se está procesando...',
            'planificacion_id': planificacion.id
        })
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ClasePlanificadaListView(generics.ListAPIView):
    serializer_class = ClasePlanificadaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.rol == 'docente':
            return ClasePlanificada.objects.filter(docente=user)
        elif user.rol == 'director':
            return ClasePlanificada.objects.filter(planificacion__director=user)
        elif user.rol == 'administrador':
            return ClasePlanificada.objects.all()
        return ClasePlanificada.objects.none()