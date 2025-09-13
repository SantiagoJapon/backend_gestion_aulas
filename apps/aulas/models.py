# apps/aulas/models.py  
from django.db import models
from django.contrib import admin

class TipoAula(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    
    def __str__(self):
        return self.nombre

class Aula(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    tipo = models.ForeignKey(TipoAula, on_delete=models.CASCADE)
    capacidad = models.PositiveIntegerField()
    piso = models.PositiveIntegerField()
    edificio = models.CharField(max_length=50)
    is_disponible = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"