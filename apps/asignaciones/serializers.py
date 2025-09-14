from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import AsignacionDocente, HorarioClase, ConflictoHorario, RegistroAsistencia
from apps.planificacion.models import PlanificacionAcademica, Materia, FranjaHoraria
from apps.aulas.models import Aula

User = get_user_model()


class AsignacionDocenteSerializer(serializers.ModelSerializer):
    docente_nombre = serializers.CharField(source='docente.get_full_name', read_only=True)
    materia_nombre = serializers.CharField(source='materia.nombre', read_only=True)
    materia_codigo = serializers.CharField(source='materia.codigo', read_only=True)
    planificacion_nombre = serializers.CharField(source='planificacion.nombre', read_only=True)
    total_horarios = serializers.SerializerMethodField()

    class Meta:
        model = AsignacionDocente
        fields = [
            'id', 'docente', 'docente_nombre', 'materia', 'materia_nombre',
            'materia_codigo', 'planificacion', 'planificacion_nombre',
            'carga_horaria_semanal', 'observaciones', 'fecha_asignacion',
            'is_activa', 'total_horarios'
        ]

    def get_total_horarios(self, obj):
        return HorarioClase.objects.filter(asignacion_docente=obj, is_activa=True).count()


class HorarioClaseSerializer(serializers.ModelSerializer):
    docente_nombre = serializers.CharField(source='asignacion_docente.docente.get_full_name', read_only=True)
    materia_nombre = serializers.CharField(source='asignacion_docente.materia.nombre', read_only=True)
    materia_codigo = serializers.CharField(source='asignacion_docente.materia.codigo', read_only=True)
    aula_codigo = serializers.CharField(source='aula.codigo', read_only=True)
    aula_nombre = serializers.CharField(source='aula.nombre', read_only=True)
    franja_nombre = serializers.CharField(source='franja_horaria.nombre', read_only=True)
    dia_semana = serializers.CharField(source='franja_horaria.dia_semana', read_only=True)
    hora_inicio = serializers.TimeField(source='franja_horaria.hora_inicio', read_only=True)
    hora_fin = serializers.TimeField(source='franja_horaria.hora_fin', read_only=True)

    class Meta:
        model = HorarioClase
        fields = [
            'id', 'asignacion_docente', 'franja_horaria', 'aula',
            'docente_nombre', 'materia_nombre', 'materia_codigo',
            'aula_codigo', 'aula_nombre', 'franja_nombre',
            'dia_semana', 'hora_inicio', 'hora_fin',
            'capacidad_estudiantes', 'modalidad', 'observaciones',
            'fecha_creacion', 'is_activa'
        ]


class HorarioClaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorarioClase
        fields = [
            'asignacion_docente', 'franja_horaria', 'aula',
            'capacidad_estudiantes', 'modalidad', 'observaciones'
        ]

    def validate(self, data):
        """Validaciones personalizadas"""
        asignacion = data['asignacion_docente']
        franja = data['franja_horaria']
        aula = data['aula']

        # 1. Validar que el docente no tenga otra clase en la misma franja
        conflicto_docente = HorarioClase.objects.filter(
            asignacion_docente__docente=asignacion.docente,
            franja_horaria=franja,
            is_activa=True
        ).exclude(id=self.instance.id if self.instance else None).exists()

        if conflicto_docente:
            raise serializers.ValidationError(
                f"El docente {asignacion.docente.get_full_name()} ya tiene una clase en {franja.nombre}"
            )

        # 2. Validar que el aula no esté ocupada
        conflicto_aula = HorarioClase.objects.filter(
            aula=aula,
            franja_horaria=franja,
            is_activa=True
        ).exclude(id=self.instance.id if self.instance else None).exists()

        if conflicto_aula:
            raise serializers.ValidationError(
                f"El aula {aula.codigo} ya está ocupada en {franja.nombre}"
            )

        # 3. Validar capacidad
        capacidad_estudiantes = data.get('capacidad_estudiantes', 0)
        if capacidad_estudiantes and capacidad_estudiantes > aula.capacidad:
            raise serializers.ValidationError(
                f"La capacidad de estudiantes ({capacidad_estudiantes}) excede la capacidad del aula ({aula.capacidad})"
            )

        return data


class ConflictoHorarioSerializer(serializers.ModelSerializer):
    planificacion_nombre = serializers.CharField(source='planificacion.nombre', read_only=True)

    class Meta:
        model = ConflictoHorario
        fields = [
            'id', 'planificacion', 'planificacion_nombre', 'tipo', 'descripcion',
            'estado', 'fecha_deteccion', 'fecha_resolucion'
        ]


class RegistroAsistenciaSerializer(serializers.ModelSerializer):
    horario_info = serializers.SerializerMethodField()

    class Meta:
        model = RegistroAsistencia
        fields = [
            'id', 'horario_clase', 'horario_info', 'fecha', 'total_estudiantes',
            'estudiantes_presentes', 'porcentaje_asistencia', 'observaciones'
        ]

    def get_horario_info(self, obj):
        return {
            'materia': obj.horario_clase.asignacion_docente.materia.nombre,
            'docente': obj.horario_clase.asignacion_docente.docente.get_full_name(),
            'aula': obj.horario_clase.aula.codigo,
            'franja': obj.horario_clase.franja_horaria.nombre
        }


# Serializers para vistas de resumen y estadísticas

class HorarioResumenSerializer(serializers.Serializer):
    """Serializer para vista resumen de horarios"""
    planificacion_id = serializers.IntegerField()
    planificacion_nombre = serializers.CharField()
    total_horarios = serializers.IntegerField()
    horarios_por_dia = serializers.DictField()
    uso_aulas = serializers.DictField()
    carga_docentes = serializers.DictField()


class ConflictoResumenSerializer(serializers.Serializer):
    """Serializer para resumen de conflictos"""
    total_conflictos = serializers.IntegerField()
    conflictos_por_tipo = serializers.DictField()
    conflictos_pendientes = serializers.IntegerField()
    conflictos_resueltos = serializers.IntegerField()