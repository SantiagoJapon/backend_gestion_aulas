from rest_framework import serializers
from .models import Aula, TipoAula

class TipoAulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoAula
        fields = '__all__'

class AulaSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)
    
    class Meta:
        model = Aula
        fields = '__all__'

class AulaDisponibilidadSerializer(serializers.Serializer):
    aula = AulaSerializer(read_only=True)
    disponible = serializers.BooleanField()
    proxima_clase = serializers.CharField(allow_null=True)
    ocupado_hasta = serializers.TimeField(allow_null=True)