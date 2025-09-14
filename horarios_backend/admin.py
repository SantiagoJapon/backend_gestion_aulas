from django.contrib import admin
from django.contrib.admin import AdminSite
from django.urls import reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.db.models import Count


class CustomAdminSite(AdminSite):
    site_header = 'Sistema de Gestión de Aulas'
    site_title = 'Gestión de Aulas'
    index_title = 'Administración del Sistema'

    def index(self, request, extra_context=None):
        """
        Vista personalizada del index del admin con estadísticas
        """
        extra_context = extra_context or {}

        try:
            from apps.usuarios.models import CustomUser
            from apps.planificacion.models import Carrera, Materia, PlanificacionAcademica
            from apps.aulas.models import Aula
            from apps.asignaciones.models import ConflictoHorario

            # Estadísticas básicas
            extra_context.update({
                'total_usuarios': CustomUser.objects.count(),
                'total_carreras': Carrera.objects.filter(is_activa=True).count(),
                'total_materias': Materia.objects.filter(is_activa=True).count(),
                'total_aulas': Aula.objects.filter(is_disponible=True).count(),

                # Datos para gráficos/tablas
                'planificaciones_recientes': PlanificacionAcademica.objects.select_related('periodo').order_by('-fecha_creacion')[:5],
                'conflictos_pendientes': ConflictoHorario.objects.filter(resuelto=False).order_by('-fecha_deteccion')[:5],

                # Estadísticas por rol
                'usuarios_por_rol': CustomUser.objects.values('rol').annotate(count=Count('id')),
                'aulas_por_edificio': Aula.objects.values('edificio').annotate(count=Count('id')),
            })

        except Exception as e:
            # En caso de error, proporcionar valores por defecto
            extra_context.update({
                'total_usuarios': 0,
                'total_carreras': 0,
                'total_materias': 0,
                'total_aulas': 0,
                'planificaciones_recientes': [],
                'conflictos_pendientes': [],
                'usuarios_por_rol': [],
                'aulas_por_edificio': [],
                'error_stats': str(e)
            })

        return super().index(request, extra_context)


# Instancia personalizada del admin
admin_site = CustomAdminSite(name='custom_admin')


# Función para personalizar el admin por defecto
def customize_default_admin():
    """Personaliza el admin site por defecto"""
    admin.site.site_header = 'Sistema de Gestión de Aulas'
    admin.site.site_title = 'Gestión de Aulas'
    admin.site.index_title = 'Panel de Administración'

customize_default_admin()