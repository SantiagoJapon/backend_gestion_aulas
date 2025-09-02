# core/models.py
from django.db import models
from django.contrib.auth.models import User

DIA_CHOICES = [('Lun','Lun'),('Mar','Mar'),('Mie','Mie'),('Jue','Jue'),('Vie','Vie'),('Sab','Sab')]
TIPO_ESPACIO = [
    ('General','General'),('Lab Informatica','Lab Informatica'),('Taller Maqueteria','Taller Maqueteria'),
    ('Sala Audiencias','Sala Audiencias'),('Lab Psicologia','Lab Psicologia'),('Auditorio','Auditorio')
]

class Aula(models.Model):
    aula_id = models.CharField(primary_key=True, max_length=50)
    edificio = models.CharField(max_length=20, blank=True)
    tipo_espacio = models.CharField(max_length=30, choices=TIPO_ESPACIO)
    capacidad = models.IntegerField(null=True, blank=True)
    equipamiento = models.TextField(blank=True)
    dias_habiles = models.CharField(max_length=50, default='Lun,Mar,Mie,Jue,Vie')
    hora_apertura = models.TimeField()
    hora_cierre = models.TimeField()
    activo = models.BooleanField(default=True)
    def __str__(self): return self.aula_id

class Docente(models.Model):
    docente_id = models.CharField(primary_key=True, max_length=50)
    nombre = models.CharField(max_length=120)
    def __str__(self): return self.nombre

class Carrera(models.Model):
    carrera = models.CharField(primary_key=True, max_length=80)
    director_titulo = models.CharField(max_length=20, blank=True)
    director_nombre = models.CharField(max_length=120, blank=True)
    coordinador_nombre = models.CharField(max_length=120, blank=True)
    def __str__(self): return self.carrera

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    docente = models.ForeignKey(Docente, null=True, blank=True, on_delete=models.SET_NULL)
    carreras = models.ManyToManyField(Carrera, blank=True, related_name="miembros")
    dirige = models.ManyToManyField(Carrera, blank=True, related_name="directores")
    def __str__(self): return self.user.username

class PreferenciaEspacio(models.Model):
    TIPO = (('reservado','reservado'),('prioridad','prioridad'))
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE)
    tipo_regla = models.CharField(max_length=20, choices=TIPO)
    class Meta:
        unique_together = ('aula','carrera','tipo_regla')

class Asignacion(models.Model):
    periodo = models.CharField(max_length=20)
    carrera = models.CharField(max_length=80)
    codigo_asignatura = models.CharField(max_length=40)
    asignatura = models.CharField(max_length=160)
    paralelo = models.CharField(max_length=10)
    docente = models.ForeignKey(Docente, null=True, blank=True, on_delete=models.SET_NULL)
    docente_nombre = models.CharField(max_length=120, blank=True)
    dia = models.CharField(max_length=3, choices=DIA_CHOICES)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    duracion_minutos = models.IntegerField(null=True, blank=True)
    estudiantes = models.IntegerField(null=True, blank=True)
    tipo_espacio = models.CharField(max_length=30, choices=TIPO_ESPACIO)
    equipamiento_requerido = models.TextField(blank=True)
    aula = models.ForeignKey(Aula, null=True, blank=True, on_delete=models.SET_NULL)
    edificio = models.CharField(max_length=20, blank=True)
    capacidad_aula = models.IntegerField(null=True, blank=True)
    conflictos_detectados = models.TextField(blank=True)
    alternativa_sugerida = models.JSONField(null=True, blank=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['periodo','codigo_asignatura','paralelo','dia','hora_inicio'], name='unique_sesion')
        ]

class Reserva(models.Model):
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE)
    usuario = models.CharField(max_length=120)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    motivo = models.CharField(max_length=200, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(hora_inicio__lt=models.F('hora_fin')), name='reserva_valida'),
            models.UniqueConstraint(fields=['aula','fecha','hora_inicio','hora_fin'], name='unique_reserva'),
        ]
