from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import TipoAula, Aula


class AulaInline(admin.TabularInline):
    model = Aula
    extra = 0
    fields = ['codigo', 'nombre', 'capacidad', 'edificio', 'piso', 'is_disponible']
    readonly_fields = []


@admin.register(TipoAula)
class TipoAulaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion', 'total_aulas']
    search_fields = ['nombre']
    inlines = [AulaInline]

    def total_aulas(self, obj):
        count = obj.aula_set.count()
        if count > 0:
            url = reverse('admin:aulas_aula_changelist') + f'?tipo__id__exact={obj.id}'
            return format_html('<a href="{}">{} aulas</a>', url, count)
        return '0 aulas'
    total_aulas.short_description = 'Total Aulas'


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'tipo', 'capacidad', 'ubicacion', 'disponibilidad_icon', 'ocupacion_actual']
    list_filter = ['tipo', 'edificio', 'piso', 'is_disponible']
    search_fields = ['codigo', 'nombre']
    ordering = ['edificio', 'piso', 'codigo']

    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'tipo')
        }),
        ('Características', {
            'fields': ('capacidad', 'edificio', 'piso')
        }),
        ('Estado', {
            'fields': ('is_disponible',)
        }),
    )

    def ubicacion(self, obj):
        return f"{obj.edificio} - Piso {obj.piso}"
    ubicacion.short_description = 'Ubicación'

    def disponibilidad_icon(self, obj):
        if obj.is_disponible:
            return format_html('<span style="color: green;">✅ Disponible</span>')
        return format_html('<span style="color: red;">❌ No disponible</span>')
    disponibilidad_icon.short_description = 'Disponibilidad'

    def ocupacion_actual(self, obj):
        try:
            from apps.asignaciones.models import HorarioClase
            count = HorarioClase.objects.filter(aula=obj, is_activa=True).count()
            if count > 0:
                return format_html('<span style="color: orange;">{} clases</span>', count)
            return format_html('<span style="color: green;">Libre</span>')
        except:
            return 'N/A'
    ocupacion_actual.short_description = 'Ocupación'

    actions = ['marcar_disponible', 'marcar_no_disponible', 'verificar_ocupacion']

    def marcar_disponible(self, request, queryset):
        count = queryset.update(is_disponible=True)
        self.message_user(request, f"Se marcaron como disponibles {count} aulas")
    marcar_disponible.short_description = "Marcar como disponibles"

    def marcar_no_disponible(self, request, queryset):
        count = queryset.update(is_disponible=False)
        self.message_user(request, f"Se marcaron como no disponibles {count} aulas")
    marcar_no_disponible.short_description = "Marcar como no disponibles"

    def verificar_ocupacion(self, request, queryset):
        try:
            from apps.asignaciones.models import HorarioClase
            total_ocupadas = 0
            for aula in queryset:
                if HorarioClase.objects.filter(aula=aula, is_activa=True).exists():
                    total_ocupadas += 1

            self.message_user(request, f"{total_ocupadas} de {queryset.count()} aulas están ocupadas")
        except:
            self.message_user(request, "Error verificando ocupación")
    verificar_ocupacion.short_description = "Verificar ocupación actual"
