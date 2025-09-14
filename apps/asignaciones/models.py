from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.usuarios.models import CustomUser
from apps.aulas.models import Aula
from apps.planificacion.models import Materia, FranjaHoraria, PlanificacionAcademica


class AsignacionDocente(models.Model):
    docente = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'rol': 'docente'},
        related_name='asignaciones_docente'
    )
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='asignaciones')
    planificacion = models.ForeignKey(PlanificacionAcademica, on_delete=models.CASCADE, related_name='asignaciones_docente')
    carga_horaria_semanal = models.PositiveIntegerField(help_text="Horas semanales asignadas")
    observaciones = models.TextField(blank=True)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    is_activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Asignación de Docente'
        verbose_name_plural = 'Asignaciones de Docentes'
        unique_together = ['docente', 'materia', 'planificacion']

    def __str__(self):
        return f"{self.docente.get_full_name()} - {self.materia.nombre}"


class HorarioClase(models.Model):
    asignacion_docente = models.ForeignKey(AsignacionDocente, on_delete=models.CASCADE, related_name='horarios')
    franja_horaria = models.ForeignKey(FranjaHoraria, on_delete=models.CASCADE, related_name='clases')
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE, related_name='clases')
    capacidad_estudiantes = models.PositiveIntegerField(default=30)
    modalidad = models.CharField(
        max_length=20,
        choices=[
            ('presencial', 'Presencial'),
            ('virtual', 'Virtual'),
            ('hibrida', 'Híbrida')
        ],
        default='presencial'
    )
    observaciones = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    is_activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Horario de Clase'
        verbose_name_plural = 'Horarios de Clases'
        unique_together = ['franja_horaria', 'aula']  # Un aula solo puede estar ocupada una vez por franja

    def clean(self):
        # Validar que la capacidad no exceda la del aula
        if self.capacidad_estudiantes and self.aula and self.capacidad_estudiantes > self.aula.capacidad:
            raise ValidationError(f'La capacidad de estudiantes ({self.capacidad_estudiantes}) excede la capacidad del aula ({self.aula.capacidad})')

        # Validar que el docente no tenga conflictos de horario
        if self.asignacion_docente and self.franja_horaria:
            conflictos = HorarioClase.objects.filter(
                asignacion_docente__docente=self.asignacion_docente.docente,
                franja_horaria=self.franja_horaria,
                is_activa=True
            ).exclude(pk=self.pk)

            if conflictos.exists():
                raise ValidationError(f'El docente {self.asignacion_docente.docente.get_full_name()} ya tiene una clase asignada en este horario')

    def __str__(self):
        return f"{self.asignacion_docente.materia.nombre} - {self.franja_horaria} - {self.aula.codigo}"


class RegistroAsistencia(models.Model):
    horario_clase = models.ForeignKey(HorarioClase, on_delete=models.CASCADE, related_name='asistencias')
    estudiante = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'rol': 'estudiante'},
        related_name='asistencias'
    )
    fecha = models.DateField()
    presente = models.BooleanField(default=False)
    tarde = models.BooleanField(default=False)
    justificada = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='registros_asistencia'
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Registro de Asistencia'
        verbose_name_plural = 'Registros de Asistencia'
        unique_together = ['horario_clase', 'estudiante', 'fecha']

    def __str__(self):
        estado = "✓" if self.presente else "✗"
        return f"{estado} {self.estudiante.get_full_name()} - {self.horario_clase.asignacion_docente.materia.nombre} ({self.fecha})"


class ConflictoHorario(models.Model):
    TIPOS_CONFLICTO = [
        ('docente_sobrecarga', 'Docente con sobrecarga horaria'),
        ('aula_ocupada', 'Aula ocupada en mismo horario'),
        ('estudiante_conflicto', 'Conflicto de horario para estudiantes'),
        ('prereq_no_cumplido', 'Prerequisito no cumplido'),
        ('capacidad_excedida', 'Capacidad del aula excedida'),
    ]

    planificacion = models.ForeignKey(PlanificacionAcademica, on_delete=models.CASCADE, related_name='conflictos')
    tipo = models.CharField(max_length=25, choices=TIPOS_CONFLICTO)
    descripcion = models.TextField()
    horario_clase = models.ForeignKey(HorarioClase, on_delete=models.CASCADE, null=True, blank=True)
    resuelto = models.BooleanField(default=False)
    fecha_deteccion = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    resuelto_por = models.ForeignKey(CustomUser, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        verbose_name = 'Conflicto de Horario'
        verbose_name_plural = 'Conflictos de Horario'
        ordering = ['-fecha_deteccion']

    def __str__(self):
        estado = "✓" if self.resuelto else "⚠️"
        return f"{estado} {self.get_tipo_display()}"

    @classmethod
    def detectar_conflictos_planificacion(cls, planificacion):
        """Detecta y crea registros de conflictos para una planificación"""
        conflictos_detectados = []

        # Limpiar conflictos anteriores no resueltos
        cls.objects.filter(planificacion=planificacion, resuelto=False).delete()

        # 1. Detectar aulas ocupadas en mismo horario
        from django.db.models import Count
        duplicados_aula = HorarioClase.objects.filter(
            asignacion_docente__planificacion=planificacion,
            is_activa=True
        ).values('franja_horaria', 'aula').annotate(
            count=Count('id')
        ).filter(count__gt=1)

        for duplicado in duplicados_aula:
            conflicto = cls.objects.create(
                planificacion=planificacion,
                tipo='aula_ocupada',
                descripcion=f"Aula ocupada múltiples veces en la misma franja horaria"
            )
            conflictos_detectados.append(conflicto)

        # 2. Detectar docentes con sobrecarga
        docentes_sobrecarga = AsignacionDocente.objects.filter(
            planificacion=planificacion,
            is_activa=True
        ).values('docente').annotate(
            total_horas=models.Sum('carga_horaria_semanal')
        ).filter(total_horas__gt=40)  # Más de 40 horas semanales

        for sobrecarga in docentes_sobrecarga:
            conflicto = cls.objects.create(
                planificacion=planificacion,
                tipo='docente_sobrecarga',
                descripcion=f"Docente con {sobrecarga['total_horas']} horas semanales (máximo recomendado: 40)"
            )
            conflictos_detectados.append(conflicto)

        return conflictos_detectados


# Métodos adicionales para HorarioClase
def agregar_metodos_horario_clase():
    def get_estudiantes_inscritos(self):
        """Retorna los estudiantes inscritos en esta clase"""
        return CustomUser.objects.filter(
            rol='estudiante',
            asistencias__horario_clase=self
        ).distinct()

    def get_porcentaje_asistencia(self, fecha_inicio=None, fecha_fin=None):
        """Calcula el porcentaje de asistencia en un rango de fechas"""
        filtros = {'horario_clase': self}
        if fecha_inicio:
            filtros['fecha__gte'] = fecha_inicio
        if fecha_fin:
            filtros['fecha__lte'] = fecha_fin

        total_registros = RegistroAsistencia.objects.filter(**filtros).count()
        if total_registros == 0:
            return 0

        presentes = RegistroAsistencia.objects.filter(**filtros, presente=True).count()
        return round((presentes / total_registros) * 100, 2)

    def tiene_conflicto_horario(self):
        """Verifica si existe conflicto de horario para este horario de clase"""
        return ConflictoHorario.objects.filter(
            horario_clase=self,
            resuelto=False
        ).exists()

    # Agregar métodos a la clase
    HorarioClase.get_estudiantes_inscritos = get_estudiantes_inscritos
    HorarioClase.get_porcentaje_asistencia = get_porcentaje_asistencia
    HorarioClase.tiene_conflicto_horario = tiene_conflicto_horario

agregar_metodos_horario_clase()