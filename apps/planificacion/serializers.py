from rest_framework import serializers
from .models import PeriodoAcademico, Materia, PlanificacionAcademica, ClasePlanificada

class PeriodoAcademicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodoAcademico
        fields = '__all__'

class MateriaSerializer(serializers.ModelSerializer):
    tipo_aula_nombre = serializers.CharField(source='tipo_aula_requerida.nombre', read_only=True)
    
    class Meta:
        model = Materia
        fields = '__all__'

class PlanificacionAcademicaSerializer(serializers.ModelSerializer):
    director_nombre = serializers.CharField(source='director.get_full_name', read_only=True)
    
    class Meta:
        model = PlanificacionAcademica
        fields = '__all__'
        
class ClasePlanificadaSerializer(serializers.ModelSerializer):
    materia_nombre = serializers.CharField(source='materia.nombre', read_only=True)
    docente_nombre = serializers.CharField(source='docente.get_full_name', read_only=True)
    
    class Meta:
        model = ClasePlanificada
        fields = '__all__'