from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg, Sum
from .models import AsignacionDocente, HorarioClase, RegistroAsistencia, ConflictoHorario


class HorarioClaseInline(admin.TabularInline):
    model = HorarioClase
    extra = 0
    fields = ['franja_horaria', 'aula', 'capacidad_estudiantes', 'modalidad', 'is_activa']
    readonly_fields = []


@admin.register(AsignacionDocente)
class AsignacionDocenteAdmin(admin.ModelAdmin):
    list_display = ['docente', 'materia', 'planificacion', 'carga_horaria_semanal', 'total_horarios', 'fecha_asignacion', 'is_activa']
    list_filter = ['planificacion', 'materia__carrera', 'is_activa', 'fecha_asignacion']
    search_fields = ['docente__first_name', 'docente__last_name', 'materia__nombre', 'materia__codigo']
    ordering = ['-fecha_asignacion']
    inlines = [HorarioClaseInline]

    fieldsets = (
        ('Asignación', {
            'fields': ('docente', 'materia', 'planificacion')
        }),
        ('Configuración', {
            'fields': ('carga_horaria_semanal', 'observaciones')
        }),
        ('Estado', {
            'fields': ('is_activa',)
        }),
        ('Auditoría', {
            'fields': ('fecha_asignacion',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['fecha_asignacion']

    def total_horarios(self, obj):
        count = obj.horarios.filter(is_activa=True).count()
        if count > 0:
            url = reverse('admin:asignaciones_horarioclase_changelist') + f'?asignacion_docente__id__exact={obj.id}'
            return format_html('<a href="{}">{} horarios</a>', url, count)
        return '0 horarios'
    total_horarios.short_description = 'Horarios'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'docente', 'materia', 'planificacion', 'materia__carrera'
        ).prefetch_related('horarios')

    actions = ['crear_horarios_automaticos', 'calcular_carga_real']

    def crear_horarios_automaticos(self, request, queryset):
        # Esta acción podría implementar un algoritmo básico de asignación
        self.message_user(request, "Funcionalidad de asignación automática en desarrollo")
    crear_horarios_automaticos.short_description = "Crear horarios automáticamente"

    def calcular_carga_real(self, request, queryset):
        for asignacion in queryset:
            total_horas = asignacion.horarios.filter(is_activa=True).count() * 1.5  # Asumiendo 1.5 horas por bloque
            if total_horas != asignacion.carga_horaria_semanal:
                asignacion.carga_horaria_semanal = int(total_horas)
                asignacion.save()

        self.message_user(request, f"Se actualizó la carga horaria de {queryset.count()} asignaciones")
    calcular_carga_real.short_description = "Actualizar carga horaria real"


class RegistroAsistenciaInline(admin.TabularInline):
    model = RegistroAsistencia
    extra = 0
    fields = ['estudiante', 'fecha', 'presente', 'tarde', 'justificada']
    readonly_fields = ['fecha_registro', 'registrado_por']


@admin.register(HorarioClase)
class HorarioClaseAdmin(admin.ModelAdmin):
    list_display = ['materia_nombre', 'docente_nombre', 'franja_horaria', 'aula', 'capacidad_estudiantes', 'modalidad', 'conflictos_status', 'is_activa']
    list_filter = ['modalidad', 'franja_horaria__dia_semana', 'aula__edificio', 'is_activa', 'asignacion_docente__materia__carrera']
    search_fields = ['asignacion_docente__materia__nombre', 'asignacion_docente__docente__first_name', 'aula__codigo']
    ordering = ['franja_horaria__dia_semana', 'franja_horaria__hora_inicio']
    inlines = [RegistroAsistenciaInline]

    fieldsets = (
        ('Asignación', {
            'fields': ('asignacion_docente', 'franja_horaria', 'aula')
        }),
        ('Configuración', {
            'fields': ('capacidad_estudiantes', 'modalidad', 'observaciones')
        }),
        ('Estado', {
            'fields': ('is_activa',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['fecha_creacion']

    def materia_nombre(self, obj):
        return obj.asignacion_docente.materia.nombre
    materia_nombre.short_description = 'Materia'

    def docente_nombre(self, obj):
        return obj.asignacion_docente.docente.get_full_name()
    docente_nombre.short_description = 'Docente'

    def conflictos_status(self, obj):
        try:
            if obj.tiene_conflicto_horario():
                return format_html('<span style="color: red;">⚠️ Conflicto</span>')
            return format_html('<span style="color: green;">✅ OK</span>')
        except:
            return '-'
    conflictos_status.short_description = 'Estado'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'asignacion_docente__materia',
            'asignacion_docente__docente',
            'franja_horaria',
            'aula'
        )

    actions = ['verificar_conflictos', 'duplicar_horario']

    def verificar_conflictos(self, request, queryset):
        conflictos_encontrados = 0
        for horario in queryset:
            try:
                if horario.tiene_conflicto_horario():
                    conflictos_encontrados += 1
            except:
                pass

        if conflictos_encontrados > 0:
            self.message_user(request, f"Se encontraron conflictos en {conflictos_encontrados} horarios", level=messages.WARNING)
        else:
            self.message_user(request, "No se encontraron conflictos en los horarios seleccionados")
    verificar_conflictos.short_description = "Verificar conflictos de horario"

    def duplicar_horario(self, request, queryset):
        duplicados = 0
        for horario in queryset:
            # Crear una copia del horario para otro día
            nuevo_horario = HorarioClase.objects.create(
                asignacion_docente=horario.asignacion_docente,
                franja_horaria=horario.franja_horaria,
                aula=horario.aula,
                capacidad_estudiantes=horario.capacidad_estudiantes,
                modalidad=horario.modalidad,
                observaciones=f"Duplicado de horario #{horario.id}"
            )
            duplicados += 1

        self.message_user(request, f"Se duplicaron {duplicados} horarios")
    duplicar_horario.short_description = "Duplicar horarios seleccionados"


@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'materia_nombre', 'fecha', 'presente_icon', 'tarde', 'justificada', 'registrado_por']
    list_filter = ['presente', 'tarde', 'justificada', 'fecha', 'horario_clase__asignacion_docente__materia']
    search_fields = ['estudiante__first_name', 'estudiante__last_name', 'horario_clase__asignacion_docente__materia__nombre']
    ordering = ['-fecha', 'estudiante__last_name']
    date_hierarchy = 'fecha'

    fieldsets = (
        ('Información Básica', {
            'fields': ('horario_clase', 'estudiante', 'fecha')
        }),
        ('Asistencia', {
            'fields': ('presente', 'tarde', 'justificada', 'observaciones')
        }),
        ('Auditoría', {
            'fields': ('registrado_por', 'fecha_registro'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['fecha_registro']

    def materia_nombre(self, obj):
        return obj.horario_clase.asignacion_docente.materia.nombre
    materia_nombre.short_description = 'Materia'

    def presente_icon(self, obj):
        if obj.presente:
            return format_html('<span style="color: green;">✅ Presente</span>')
        elif obj.justificada:
            return format_html('<span style="color: orange;">📝 Justificada</span>')
        else:
            return format_html('<span style="color: red;">❌ Ausente</span>')
    presente_icon.short_description = 'Asistencia'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)

    actions = ['marcar_como_presente', 'marcar_como_justificada']

    def marcar_como_presente(self, request, queryset):
        count = queryset.update(presente=True, tarde=False)
        self.message_user(request, f"Se marcaron como presentes {count} registros")
    marcar_como_presente.short_description = "Marcar como presente"

    def marcar_como_justificada(self, request, queryset):
        count = queryset.update(justificada=True)
        self.message_user(request, f"Se marcaron como justificadas {count} ausencias")
    marcar_como_justificada.short_description = "Marcar ausencia como justificada"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'estudiante',
            'horario_clase__asignacion_docente__materia',
            'registrado_por'
        )


@admin.register(ConflictoHorario)
class ConflictoHorarioAdmin(admin.ModelAdmin):
    list_display = ['tipo_icon', 'planificacion', 'descripcion_corta', 'resuelto_icon', 'fecha_deteccion', 'fecha_resolucion']
    list_filter = ['tipo', 'resuelto', 'fecha_deteccion']
    search_fields = ['descripcion']
    ordering = ['-fecha_deteccion']
    date_hierarchy = 'fecha_deteccion'

    fieldsets = (
        ('Conflicto', {
            'fields': ('planificacion', 'tipo', 'descripcion')
        }),
        ('Horario Relacionado', {
            'fields': ('horario_clase',),
            'classes': ('collapse',)
        }),
        ('Resolución', {
            'fields': ('resuelto', 'fecha_resolucion', 'resuelto_por')
        }),
        ('Auditoría', {
            'fields': ('fecha_deteccion',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['fecha_deteccion']

    def tipo_icon(self, obj):
        icons = {
            'docente_sobrecarga': '👨‍🏫',
            'aula_ocupada': '🏫',
            'estudiante_conflicto': '👨‍🎓',
            'prereq_no_cumplido': '📚',
            'capacidad_excedida': '👥',
        }
        icon = icons.get(obj.tipo, '⚠️')
        return f"{icon} {obj.get_tipo_display()}"
    tipo_icon.short_description = 'Tipo de Conflicto'

    def descripcion_corta(self, obj):
        return obj.descripcion[:100] + '...' if len(obj.descripcion) > 100 else obj.descripcion
    descripcion_corta.short_description = 'Descripción'

    def resuelto_icon(self, obj):
        if obj.resuelto:
            return format_html('<span style="color: green;">✅ Resuelto</span>')
        return format_html('<span style="color: red;">❌ Pendiente</span>')
    resuelto_icon.short_description = 'Estado'

    def save_model(self, request, obj, form, change):
        if obj.resuelto and not obj.fecha_resolucion:
            obj.fecha_resolucion = timezone.now()
            obj.resuelto_por = request.user
        super().save_model(request, obj, form, change)

    actions = ['marcar_como_resuelto', 'detectar_nuevos_conflictos']

    def marcar_como_resuelto(self, request, queryset):
        count = 0
        for conflicto in queryset.filter(resuelto=False):
            conflicto.resuelto = True
            conflicto.fecha_resolucion = timezone.now()
            conflicto.resuelto_por = request.user
            conflicto.save()
            count += 1

        self.message_user(request, f"Se marcaron como resueltos {count} conflictos")
    marcar_como_resuelto.short_description = "Marcar como resueltos"

    def detectar_nuevos_conflictos(self, request, queryset):
        planificaciones = set(obj.planificacion for obj in queryset)
        total_conflictos = 0

        for planificacion in planificaciones:
            conflictos = ConflictoHorario.detectar_conflictos_planificacion(planificacion)
            total_conflictos += len(conflictos)

        if total_conflictos > 0:
            self.message_user(request, f"Se detectaron {total_conflictos} nuevos conflictos", level=messages.WARNING)
        else:
            self.message_user(request, "No se detectaron nuevos conflictos")
    detectar_nuevos_conflictos.short_description = "Detectar nuevos conflictos"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'planificacion',
            'horario_clase',
            'resuelto_por'
        )