from django.db import models
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.usuarios.models import CustomUser
from apps.aulas.models import Aula


class Carrera(models.Model):
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    duracion_semestres = models.PositiveIntegerField(default=8)
    is_activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Carrera'
        verbose_name_plural = 'Carreras'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Periodo(models.Model):
    TIPOS_PERIODO = [
        ('semestre', 'Semestre'),
        ('cuatrimestre', 'Cuatrimestre'),
        ('trimestre', 'Trimestre'),
        ('anual', 'Anual'),
    ]

    nombre = models.CharField(max_length=50)
    tipo = models.CharField(max_length=15, choices=TIPOS_PERIODO, default='semestre')
    anio = models.PositiveIntegerField()
    numero = models.PositiveIntegerField(help_text="Número del periodo en el año (1, 2, etc.)")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    is_activo = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Período'
        verbose_name_plural = 'Períodos'
        ordering = ['-anio', '-numero']
        unique_together = ['anio', 'numero', 'tipo']

    def clean(self):
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_inicio >= self.fecha_fin:
                raise ValidationError('La fecha de inicio debe ser anterior a la fecha de fin')

    def __str__(self):
        return f"{self.nombre} {self.anio}"


class Materia(models.Model):
    codigo = models.CharField(max_length=15, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    creditos = models.PositiveIntegerField(default=3)
    horas_semanales = models.PositiveIntegerField(default=4)
    semestre = models.PositiveIntegerField(help_text="Semestre en el que se cursa normalmente")
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name='materias')
    prereq_materias = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='materias_dependientes')
    is_activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Materia'
        verbose_name_plural = 'Materias'
        ordering = ['carrera', 'semestre', 'nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class FranjaHoraria(models.Model):
    DIAS_SEMANA = [
        ('lunes', 'Lunes'),
        ('martes', 'Martes'),
        ('miercoles', 'Miércoles'),
        ('jueves', 'Jueves'),
        ('viernes', 'Viernes'),
        ('sabado', 'Sábado'),
        ('domingo', 'Domingo'),
    ]

    nombre = models.CharField(max_length=50, help_text="Ej: 'Bloque 1', '1era Hora'")
    dia_semana = models.CharField(max_length=10, choices=DIAS_SEMANA)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    duracion_minutos = models.PositiveIntegerField(editable=False)
    is_activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Franja Horaria'
        verbose_name_plural = 'Franjas Horarias'
        ordering = ['dia_semana', 'hora_inicio']
        unique_together = ['dia_semana', 'hora_inicio', 'hora_fin']

    def clean(self):
        if self.hora_inicio and self.hora_fin:
            if self.hora_inicio >= self.hora_fin:
                raise ValidationError('La hora de inicio debe ser anterior a la hora de fin')

    def save(self, *args, **kwargs):
        if self.hora_inicio and self.hora_fin:
            inicio = timezone.datetime.combine(timezone.datetime.today(), self.hora_inicio)
            fin = timezone.datetime.combine(timezone.datetime.today(), self.hora_fin)
            self.duracion_minutos = int((fin - inicio).total_seconds() / 60)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_dia_semana_display()} {self.hora_inicio.strftime('%H:%M')}-{self.hora_fin.strftime('%H:%M')}"


class PlanificacionAcademica(models.Model):
    ESTADOS = [
        ('borrador', 'Borrador'),
        ('revision', 'En Revisión'),
        ('aprobada', 'Aprobada'),
        ('vigente', 'Vigente'),
        ('cerrada', 'Cerrada'),
    ]

    nombre = models.CharField(max_length=100)
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name='planificaciones')
    carreras = models.ManyToManyField(Carrera, related_name='planificaciones')
    estado = models.CharField(max_length=15, choices=ESTADOS, default='borrador')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='planificaciones_creadas')
    aprobado_por = models.ForeignKey(CustomUser, on_delete=models.PROTECT, null=True, blank=True, related_name='planificaciones_aprobadas')
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Planificación Académica'
        verbose_name_plural = 'Planificaciones Académicas'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.nombre} - {self.periodo}"

    def get_total_materias(self):
        """Retorna el total de materias en la planificación"""
        return sum(carrera.materias.filter(is_activa=True).count() for carrera in self.carreras.all())

    def get_total_horas_semanales(self):
        """Retorna el total de horas semanales planificadas"""
        total_horas = 0
        for carrera in self.carreras.all():
            total_horas += sum(materia.horas_semanales for materia in carrera.materias.filter(is_activa=True))
        return total_horas

    def activar(self, usuario):
        """Activa la planificación como vigente"""
        if self.estado == 'aprobada':
            # Desactivar otras planificaciones vigentes del mismo periodo
            PlanificacionAcademica.objects.filter(
                periodo=self.periodo,
                estado='vigente'
            ).update(estado='cerrada')

            self.estado = 'vigente'
            self.fecha_aprobacion = timezone.now()
            self.aprobado_por = usuario
            self.save()
