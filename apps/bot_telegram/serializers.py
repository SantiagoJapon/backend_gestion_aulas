from rest_framework import serializers
from .models import SolicitudReserva, ConsultaBot

class SolicitudReservaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.get_full_name', read_only=True)
    aula_codigo = serializers.CharField(source='aula.codigo', read_only=True)
    
    class Meta:
        model = SolicitudReserva
        fields = '__all__'

class ConsultaBotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultaBot
        fields = '__all__'