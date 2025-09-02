from django.db import models
from django.contrib.auth import get_user_model
from apps.aulas.models import Aula, TipoAula

User = get_user_model()

class PeriodoAcademico(models.Model):
    nombre = models.CharField(max_length=50)  # "2024-1", "2024-2"
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    is_activo = models.BooleanField(default=False)
    
    def __str__(self):
        return self.nombre

class Materia(models.Model):
    JORNADAS = [
        ('matutina', 'Matutina'),
        ('vespertina', 'Vespertina'),
        ('nocturna', 'Nocturna'),
    ]
    
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=200)
    creditos = models.PositiveIntegerField()
    carrera = models.CharField(max_length=100)
    nivel = models.PositiveIntegerField()
    tipo_aula_requerida = models.ForeignKey(TipoAula, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class PlanificacionAcademica(models.Model):
    ESTADOS = [
        ('cargada', 'Cargada'),
        ('procesando', 'Procesando'),
        ('asignada', 'Asignada'),
        ('con_conflictos', 'Con Conflictos'),
    ]
    
    periodo = models.ForeignKey(PeriodoAcademico, on_delete=models.CASCADE)
    director = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'rol': 'director'})
    carrera = models.CharField(max_length=100)
    archivo_planificacion = models.FileField(upload_to='planificaciones/')
    fecha_carga = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='cargada')
    observaciones = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['periodo', 'carrera']
    
    def __str__(self):
        return f"{self.carrera} - {self.periodo.nombre}"

class ClasePlanificada(models.Model):
    DIAS_SEMANA = [
        ('lunes', 'Lunes'),
        ('martes', 'Martes'),
        ('miercoles', 'Miércoles'),
        ('jueves', 'Jueves'),
        ('viernes', 'Viernes'),
        ('sabado', 'Sábado'),
    ]
    
    planificacion = models.ForeignKey(PlanificacionAcademica, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    docente = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'rol': 'docente'})
    paralelo = models.CharField(max_length=10)
    numero_estudiantes = models.PositiveIntegerField()
    dia_semana = models.CharField(max_length=10, choices=DIAS_SEMANA)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    tipo_clase = models.CharField(max_length=50)  # Teórica, Práctica
    
    def __str__(self):
        return f"{self.materia.nombre} - {self.paralelo} - {self.dia_semana}"