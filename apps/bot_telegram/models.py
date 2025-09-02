from django.db import models
from django.contrib.auth import get_user_model
from apps.aulas.models import Aula

User = get_user_model()

class SolicitudReserva(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('cancelada', 'Cancelada'),
    ]
    
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'rol': 'estudiante'})
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE)
    fecha_reserva = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    proposito = models.CharField(max_length=200)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    telegram_message_id = models.CharField(max_length=50, blank=True)
    
    class Meta:
        unique_together = ['aula', 'fecha_reserva', 'hora_inicio', 'hora_fin']
    
    def __str__(self):
        return f"{self.estudiante.username} - {self.aula.codigo} - {self.fecha_reserva}"

class ConsultaBot(models.Model):
    TIPOS_CONSULTA = [
        ('disponibilidad_aula', 'Disponibilidad de Aula'),
        ('ubicacion_docente', 'Ubicación de Docente'),
        ('reserva_aula', 'Reserva de Aula'),
        ('horario_personal', 'Horario Personal'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    tipo_consulta = models.CharField(max_length=30, choices=TIPOS_CONSULTA)
    consulta_texto = models.TextField()
    respuesta = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    telegram_chat_id = models.CharField(max_length=50)
    
    def __str__(self):
        return f"{self.usuario.username} - {self.get_tipo_consulta_display()}"