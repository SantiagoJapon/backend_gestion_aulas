from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Periodo, Carrera, Materia, FranjaHoraria, PlanificacionAcademica
from apps.asignaciones.models import AsignacionDocente, HorarioClase, ConflictoHorario

User = get_user_model()


class PeriodoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Periodo
        fields = ['id', 'nombre', 'tipo', 'anio', 'numero', 'fecha_inicio', 'fecha_fin', 'is_activo']


class CarreraSerializer(serializers.ModelSerializer):
    total_materias = serializers.SerializerMethodField()

    class Meta:
        model = Carrera
        fields = ['id', 'codigo', 'nombre', 'descripcion', 'total_materias', 'fecha_creacion']

    def get_total_materias(self, obj):
        return obj.materias.filter(is_activa=True).count()


class MateriaSerializer(serializers.ModelSerializer):
    carrera_nombre = serializers.CharField(source='carrera.nombre', read_only=True)
    prereq_materias_nombres = serializers.SerializerMethodField()

    class Meta:
        model = Materia
        fields = [
            'id', 'codigo', 'nombre', 'descripcion', 'creditos', 'horas_semanales',
            'semestre', 'carrera', 'carrera_nombre', 'prereq_materias',
            'prereq_materias_nombres', 'is_activa'
        ]

    def get_prereq_materias_nombres(self, obj):
        return [m.nombre for m in obj.prereq_materias.all()]


class FranjaHorariaSerializer(serializers.ModelSerializer):
    duracion_formateada = serializers.SerializerMethodField()

    class Meta:
        model = FranjaHoraria
        fields = ['id', 'nombre', 'dia_semana', 'hora_inicio', 'hora_fin',
                 'duracion_minutos', 'duracion_formateada']

    def get_duracion_formateada(self, obj):
        horas = obj.duracion_minutos // 60
        minutos = obj.duracion_minutos % 60
        return f"{horas}h {minutos}m" if minutos > 0 else f"{horas}h"


class DocenteBasicoSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'nombre_completo', 'rol']


class AsignacionDocenteSerializer(serializers.ModelSerializer):
    docente = DocenteBasicoSerializer(read_only=True)
    docente_id = serializers.IntegerField(write_only=True)
    materia = MateriaSerializer(read_only=True)
    materia_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = AsignacionDocente
        fields = [
            'id', 'docente', 'docente_id', 'materia', 'materia_id',
            'carga_horaria_semanal', 'observaciones', 'fecha_asignacion', 'is_activa'
        ]

    def validate_docente_id(self, value):
        try:
            docente = User.objects.get(id=value, rol='docente')
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Docente no encontrado o no tiene rol de docente")


class HorarioClaseSerializer(serializers.ModelSerializer):
    asignacion_docente = AsignacionDocenteSerializer(read_only=True)
    franja_horaria = FranjaHorariaSerializer(read_only=True)
    aula_codigo = serializers.CharField(source='aula.codigo', read_only=True)
    aula_nombre = serializers.CharField(source='aula.nombre', read_only=True)

    class Meta:
        model = HorarioClase
        fields = [
            'id', 'asignacion_docente', 'franja_horaria', 'aula_codigo', 'aula_nombre',
            'capacidad_estudiantes', 'modalidad', 'observaciones', 'fecha_creacion', 'is_activa'
        ]


class ConflictoHorarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConflictoHorario
        fields = ['id', 'tipo', 'descripcion', 'estado', 'fecha_deteccion', 'fecha_resolucion']


class PlanificacionAcademicaListSerializer(serializers.ModelSerializer):
    periodo_nombre = serializers.CharField(source='periodo.nombre', read_only=True)
    creado_por_nombre = serializers.CharField(source='creado_por.get_full_name', read_only=True)
    total_asignaciones = serializers.SerializerMethodField()
    total_horarios = serializers.SerializerMethodField()
    total_conflictos = serializers.SerializerMethodField()
    progreso = serializers.SerializerMethodField()

    class Meta:
        model = PlanificacionAcademica
        fields = [
            'id', 'nombre', 'periodo', 'periodo_nombre', 'estado', 'fecha_creacion',
            'creado_por', 'creado_por_nombre', 'total_asignaciones', 'total_horarios',
            'total_conflictos', 'progreso'
        ]

    def get_total_asignaciones(self, obj):
        return obj.asignaciones_docente.filter(is_activa=True).count()

    def get_total_horarios(self, obj):
        return HorarioClase.objects.filter(
            asignacion_docente__planificacion=obj,
            is_activa=True
        ).count()

    def get_total_conflictos(self, obj):
        return ConflictoHorario.objects.filter(
            planificacion=obj,
            estado='pendiente'
        ).count()

    def get_progreso(self, obj):
        total_asignaciones = self.get_total_asignaciones(obj)
        total_horarios = self.get_total_horarios(obj)
        if total_asignaciones == 0:
            return 0
        return round((total_horarios / total_asignaciones) * 100, 1)


class PlanificacionAcademicaDetailSerializer(serializers.ModelSerializer):
    periodo = PeriodoSerializer(read_only=True)
    carreras = CarreraSerializer(many=True, read_only=True)
    creado_por = DocenteBasicoSerializer(read_only=True)
    aprobado_por = DocenteBasicoSerializer(read_only=True)
    asignaciones_docente = AsignacionDocenteSerializer(many=True, read_only=True)
    horarios = serializers.SerializerMethodField()
    conflictos = serializers.SerializerMethodField()
    estadisticas = serializers.SerializerMethodField()

    class Meta:
        model = PlanificacionAcademica
        fields = [
            'id', 'nombre', 'periodo', 'carreras', 'estado', 'observaciones',
            'fecha_creacion', 'fecha_aprobacion', 'creado_por', 'aprobado_por',
            'asignaciones_docente', 'horarios', 'conflictos', 'estadisticas'
        ]

    def get_horarios(self, obj):
        horarios = HorarioClase.objects.filter(
            asignacion_docente__planificacion=obj,
            is_activa=True
        ).select_related('asignacion_docente__docente', 'asignacion_docente__materia', 'franja_horaria', 'aula')
        return HorarioClaseSerializer(horarios, many=True).data

    def get_conflictos(self, obj):
        conflictos = ConflictoHorario.objects.filter(planificacion=obj, estado='pendiente')
        return ConflictoHorarioSerializer(conflictos, many=True).data

    def get_estadisticas(self, obj):
        asignaciones_activas = obj.asignaciones_docente.filter(is_activa=True)
        horarios_activos = HorarioClase.objects.filter(
            asignacion_docente__planificacion=obj,
            is_activa=True
        )

        # Estadísticas por día
        dias_stats = {}
        for horario in horarios_activos:
            dia = horario.franja_horaria.get_dia_semana_display()
            if dia not in dias_stats:
                dias_stats[dia] = 0
            dias_stats[dia] += 1

        # Estadísticas por aula
        aulas_stats = {}
        for horario in horarios_activos:
            aula = horario.aula.codigo
            if aula not in aulas_stats:
                aulas_stats[aula] = 0
            aulas_stats[aula] += 1

        return {
            'total_docentes': asignaciones_activas.values('docente').distinct().count(),
            'total_materias': asignaciones_activas.values('materia').distinct().count(),
            'total_horas_semanales': sum(a.carga_horaria_semanal for a in asignaciones_activas),
            'horarios_por_dia': dias_stats,
            'uso_de_aulas': aulas_stats,
            'cobertura_horaria': round(
                (horarios_activos.count() / max(asignaciones_activas.count(), 1)) * 100, 1
            )
        }


class PlanificacionAcademicaCreateSerializer(serializers.ModelSerializer):
    carreras_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=True
    )

    class Meta:
        model = PlanificacionAcademica
        fields = ['nombre', 'periodo', 'observaciones', 'carreras_ids']

    def create(self, validated_data):
        carreras_ids = validated_data.pop('carreras_ids')
        validated_data['creado_por'] = self.context['request'].user
        planificacion = PlanificacionAcademica.objects.create(**validated_data)

        # Agregar carreras
        carreras = Carrera.objects.filter(id__in=carreras_ids)
        planificacion.carreras.set(carreras)

        return planificacion

    def validate_carreras_ids(self, value):
        if not value:
            raise serializers.ValidationError("Debe seleccionar al menos una carrera")

        existing_carreras = Carrera.objects.filter(id__in=value).count()
        if existing_carreras != len(value):
            raise serializers.ValidationError("Una o más carreras no existen")

        return value


class PlanificacionAcademicaUpdateSerializer(serializers.ModelSerializer):
    carreras_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = PlanificacionAcademica
        fields = ['nombre', 'observaciones', 'carreras_ids']

    def update(self, instance, validated_data):
        carreras_ids = validated_data.pop('carreras_ids', None)

        # Validar que solo se pueda editar en estado borrador
        if instance.estado not in ['borrador']:
            raise serializers.ValidationError(
                "Solo se pueden editar planificaciones en estado 'borrador'"
            )

        # Actualizar campos básicos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Actualizar carreras si se proporcionaron
        if carreras_ids is not None:
            carreras = Carrera.objects.filter(id__in=carreras_ids)
            instance.carreras.set(carreras)

        return instance