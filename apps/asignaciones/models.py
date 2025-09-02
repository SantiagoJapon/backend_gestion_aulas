from django.db import models
from apps.planificacion.models import ClasePlanificada
from apps.aulas.models import Aula

class AsignacionAula(models.Model):
    ESTADOS = [
        ('asignada', 'Asignada'),
        ('confirmada', 'Confirmada'),
        ('rechazada', 'Rechazada'),
    ]
    
    clase_planificada = models.OneToOneField(ClasePlanificada, on_delete=models.CASCADE)
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='asignada')
    prioridad = models.PositiveIntegerField(default=1)
    observaciones = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['aula', 'clase_planificada']
    
    def __str__(self):
        return f"{self.aula.codigo} - {self.clase_planificada}"

class ConflictoHorario(models.Model):
    TIPOS = [
        ('aula_ocupada', 'Aula Ocupada'),
        ('docente_ocupado', 'Docente Ocupado'),
        ('capacidad_insuficiente', 'Capacidad Insuficiente'),
        ('tipo_aula_incorrecto', 'Tipo de Aula Incorrecto'),
    ]
    
    ESTADOS = [
        ('detectado', 'Detectado'),
        ('resuelto_auto', 'Resuelto Automáticamente'),
        ('resuelto_manual', 'Resuelto Manualmente'),
        ('pendiente', 'Pendiente'),
    ]
    
    clase_planificada = models.ForeignKey(ClasePlanificada, on_delete=models.CASCADE)
    tipo_conflicto = models.CharField(max_length=30, choices=TIPOS)
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='detectado')
    fecha_deteccion = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    solucion_aplicada = models.TextField(blank=True)
    
    def __str__(self):
        return f"Conflicto: {self.get_tipo_conflicto_display()} - {self.clase_planificada}"