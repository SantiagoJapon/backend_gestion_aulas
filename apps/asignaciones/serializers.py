from rest_framework import serializers
from .models import AsignacionAula, ConflictoHorario

class AsignacionAulaSerializer(serializers.ModelSerializer):
    aula_nombre = serializers.CharField(source='aula.nombre', read_only=True)
    aula_codigo = serializers.CharField(source='aula.codigo', read_only=True)
    materia_nombre = serializers.CharField(source='clase_planificada.materia.nombre', read_only=True)
    docente_nombre = serializers.CharField(source='clase_planificada.docente.get_full_name', read_only=True)
    
    class Meta:
        model = AsignacionAula
        fields = '__all__'

class ConflictoHorarioSerializer(serializers.ModelSerializer):
    materia_nombre = serializers.CharField(source='clase_planificada.materia.nombre', read_only=True)
    
    class Meta:
        model = ConflictoHorario
        fields = '__all__'