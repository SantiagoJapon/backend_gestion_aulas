from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import AsignacionAula, ConflictoHorario
from .serializers import AsignacionAulaSerializer, ConflictoHorarioSerializer

class AsignacionAulaListView(generics.ListAPIView):
    serializer_class = AsignacionAulaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.rol == 'docente':
            return AsignacionAula.objects.filter(clase_planificada__docente=user)
        elif user.rol == 'director':
            return AsignacionAula.objects.filter(clase_planificada__planificacion__director=user)
        elif user.rol == 'administrador':
            return AsignacionAula.objects.all()
        return AsignacionAula.objects.none()

class ConflictoHorarioListView(generics.ListAPIView):
    serializer_class = ConflictoHorarioSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.rol == 'administrador':
            return ConflictoHorario.objects.filter(estado__in=['detectado', 'pendiente'])
        elif user.rol == 'director':
            return ConflictoHorario.objects.filter(
                clase_planificada__planificacion__director=user,
                estado__in=['detectado', 'pendiente']
            )
        return ConflictoHorario.objects.none()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resolver_conflicto_view(request, conflicto_id):
    """Vista para resolver conflictos manualmente"""
    if request.user.rol not in ['administrador', 'director']:
        return Response