from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils import timezone
from .models import Carrera, Periodo, Materia, FranjaHoraria, PlanificacionAcademica


@admin.register(Carrera)
class CarreraAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'duracion_semestres', 'is_activa', 'total_materias', 'created_at']
    list_filter = ['is_activa', 'duracion_semestres', 'created_at']
    search_fields = ['codigo', 'nombre']
    ordering = ['codigo']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (None, {
            'fields': ('codigo', 'nombre', 'descripcion')
        }),
        ('Configuración', {
            'fields': ('duracion_semestres', 'is_activa')
        }),
        ('Información del Sistema', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def total_materias(self, obj):
        count = obj.materias.filter(is_activa=True).count()
        if count > 0:
            url = reverse('admin:planificacion_materia_changelist') + f'?carrera__id__exact={obj.id}'
            return format_html('<a href="{}">{} materias</a>', url, count)
        return '0 materias'
    total_materias.short_description = 'Total Materias'


@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'anio', 'numero', 'fecha_inicio', 'fecha_fin', 'is_activo', 'duracion_dias']
    list_filter = ['tipo', 'anio', 'is_activo']
    search_fields = ['nombre']
    ordering = ['-anio', '-numero']

    fieldsets = (
        (None, {
            'fields': ('nombre', 'tipo', 'anio', 'numero')
        }),
        ('Fechas', {
            'fields': ('fecha_inicio', 'fecha_fin')
        }),
        ('Estado', {
            'fields': ('is_activo',)
        }),
    )

    def duracion_dias(self, obj):
        if obj.fecha_inicio and obj.fecha_fin:
            delta = obj.fecha_fin - obj.fecha_inicio
            return f"{delta.days} días"
        return '-'
    duracion_dias.short_description = 'Duración'

    actions = ['activar_periodo', 'desactivar_periodo']

    def activar_periodo(self, request, queryset):
        for periodo in queryset:
            # Desactivar otros períodos del mismo año y tipo
            Periodo.objects.filter(anio=periodo.anio, tipo=periodo.tipo).update(is_activo=False)
            periodo.is_activo = True
            periodo.save()
        self.message_user(request, f"Se activaron {queryset.count()} períodos")
    activar_periodo.short_description = "Activar períodos seleccionados"

    def desactivar_periodo(self, request, queryset):
        queryset.update(is_activo=False)
        self.message_user(request, f"Se desactivaron {queryset.count()} períodos")
    desactivar_periodo.short_description = "Desactivar períodos seleccionados"


class MateriaInline(admin.TabularInline):
    model = Materia
    extra = 0
    fields = ['codigo', 'nombre', 'creditos', 'horas_semanales', 'semestre', 'is_activa']
    readonly_fields = []


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'carrera', 'semestre', 'creditos', 'horas_semanales', 'prereq_count', 'is_activa']
    list_filter = ['carrera', 'semestre', 'creditos', 'is_activa']
    search_fields = ['codigo', 'nombre']
    ordering = ['carrera', 'semestre', 'codigo']
    filter_horizontal = ['prereq_materias']

    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'descripcion', 'carrera')
        }),
        ('Configuración Académica', {
            'fields': ('creditos', 'horas_semanales', 'semestre')
        }),
        ('Prerrequisitos', {
            'fields': ('prereq_materias',),
            'description': 'Selecciona las materias que son prerrequisito para esta materia'
        }),
        ('Estado', {
            'fields': ('is_activa',)
        }),
    )

    def prereq_count(self, obj):
        count = obj.prereq_materias.count()
        if count > 0:
            return f"{count} materias"
        return "Sin prerrequisitos"
    prereq_count.short_description = 'Prerrequisitos'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('carrera').prefetch_related('prereq_materias')


@admin.register(FranjaHoraria)
class FranjaHorariaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'dia_semana', 'hora_inicio', 'hora_fin', 'duracion_minutos', 'is_activa', 'total_clases']
    list_filter = ['dia_semana', 'is_activa']
    search_fields = ['nombre']
    ordering = ['dia_semana', 'hora_inicio']

    fieldsets = (
        (None, {
            'fields': ('nombre', 'dia_semana')
        }),
        ('Horario', {
            'fields': ('hora_inicio', 'hora_fin'),
            'description': 'La duración se calculará automáticamente'
        }),
        ('Estado', {
            'fields': ('is_activa',)
        }),
    )

    readonly_fields = ['duracion_minutos']

    def total_clases(self, obj):
        try:
            from apps.asignaciones.models import HorarioClase
            count = HorarioClase.objects.filter(franja_horaria=obj, is_activa=True).count()
            if count > 0:
                return format_html('<span style="color: orange;">{} clases</span>', count)
            return '0 clases'
        except:
            return '0 clases'
    total_clases.short_description = 'Clases Asignadas'

    actions = ['duplicar_franja_todos_dias']

    def duplicar_franja_todos_dias(self, request, queryset):
        dias_semana = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
        total_creadas = 0

        for franja in queryset:
            for dia in dias_semana:
                if dia != franja.dia_semana:
                    nueva_franja, created = FranjaHoraria.objects.get_or_create(
                        nombre=franja.nombre,
                        dia_semana=dia,
                        hora_inicio=franja.hora_inicio,
                        hora_fin=franja.hora_fin,
                        defaults={'is_activa': True}
                    )
                    if created:
                        total_creadas += 1

        self.message_user(request, f"Se crearon {total_creadas} nuevas franjas horarias")
    duplicar_franja_todos_dias.short_description = "Duplicar franja para todos los días"


@admin.register(PlanificacionAcademica)
class PlanificacionAcademicaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'periodo', 'estado', 'total_carreras', 'total_materias_display', 'creado_por', 'fecha_creacion']
    list_filter = ['estado', 'periodo__anio', 'fecha_creacion']
    search_fields = ['nombre', 'observaciones']
    ordering = ['-fecha_creacion']
    filter_horizontal = ['carreras']
    readonly_fields = ['fecha_creacion', 'fecha_aprobacion', 'total_materias_display', 'total_horas_display']

    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'periodo', 'carreras')
        }),
        ('Estado', {
            'fields': ('estado', 'observaciones')
        }),
        ('Estadísticas', {
            'fields': ('total_materias_display', 'total_horas_display'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'aprobado_por', 'fecha_aprobacion'),
            'classes': ('collapse',)
        }),
    )

    def total_carreras(self, obj):
        return obj.carreras.count()
    total_carreras.short_description = 'Carreras'

    def total_materias_display(self, obj):
        return obj.get_total_materias()
    total_materias_display.short_description = 'Total Materias'

    def total_horas_display(self, obj):
        return f"{obj.get_total_horas_semanales()} horas/semana"
    total_horas_display.short_description = 'Total Horas'

    def save_model(self, request, obj, form, change):
        if not change:  # Si es una nueva planificación
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)

    actions = ['aprobar_planificacion', 'activar_planificacion', 'detectar_conflictos']

    def aprobar_planificacion(self, request, queryset):
        count = 0
        for planificacion in queryset.filter(estado='revision'):
            planificacion.estado = 'aprobada'
            planificacion.aprobado_por = request.user
            planificacion.fecha_aprobacion = timezone.now()
            planificacion.save()
            count += 1

        if count > 0:
            self.message_user(request, f"Se aprobaron {count} planificaciones")
        else:
            self.message_user(request, "No hay planificaciones en estado 'En Revisión' para aprobar", level=messages.WARNING)
    aprobar_planificacion.short_description = "Aprobar planificaciones en revisión"

    def activar_planificacion(self, request, queryset):
        count = 0
        for planificacion in queryset.filter(estado='aprobada'):
            planificacion.activar(request.user)
            count += 1

        if count > 0:
            self.message_user(request, f"Se activaron {count} planificaciones")
        else:
            self.message_user(request, "No hay planificaciones aprobadas para activar", level=messages.WARNING)
    activar_planificacion.short_description = "Activar planificaciones aprobadas"

    def detectar_conflictos(self, request, queryset):
        try:
            from apps.asignaciones.models import ConflictoHorario
            total_conflictos = 0

            for planificacion in queryset:
                conflictos = ConflictoHorario.detectar_conflictos_planificacion(planificacion)
                total_conflictos += len(conflictos)

            if total_conflictos > 0:
                self.message_user(request, f"Se detectaron {total_conflictos} conflictos", level=messages.WARNING)
            else:
                self.message_user(request, "No se detectaron conflictos")
        except Exception as e:
            self.message_user(request, f"Error detectando conflictos: {e}", level=messages.ERROR)
    detectar_conflictos.short_description = "Detectar conflictos de horario"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('periodo', 'creado_por', 'aprobado_por').prefetch_related('carreras')