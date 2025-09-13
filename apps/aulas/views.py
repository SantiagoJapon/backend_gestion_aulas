from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.http import JsonResponse
from .models import Aula, TipoAula

class AulaListView(generics.ListAPIView):
    queryset = Aula.objects.all()
    permission_classes = [AllowAny]
    
    def list(self, request, *args, **kwargs):
        aulas = Aula.objects.all()
        data = []
        for aula in aulas:
            data.append({
                'id': aula.id,
                'codigo': aula.codigo,
                'nombre': aula.nombre,
                'capacidad': aula.capacidad,
                'edificio': aula.edificio,
                'piso': aula.piso,
                'is_disponible': aula.is_disponible
            })
        return Response({'aulas': data})