# apps/usuarios/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLES = [
        ('estudiante', 'Estudiante'),
        ('docente', 'Docente'),
        ('director', 'Director'),
        ('administrador', 'Administrador'),
    ]
    
    rol = models.CharField(max_length=20, choices=ROLES, default='estudiante')
    cedula = models.CharField(max_length=10, unique=True, null=True, blank=True)
    telegram_id = models.CharField(max_length=50, blank=True, null=True)
    
    def __str__(self):
        return self.username