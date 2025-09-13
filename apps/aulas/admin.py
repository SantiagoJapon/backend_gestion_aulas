from django.contrib import admin
from .models import TipoAula, Aula

@admin.register(TipoAula)
class TipoAulaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion']
    search_fields = ['nombre']

@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'tipo', 'capacidad', 'edificio', 'piso', 'is_disponible']
    list_filter = ['tipo', 'edificio', 'is_disponible']
    search_fields = ['codigo', 'nombre']
    ordering = ['edificio', 'piso', 'codigo']
