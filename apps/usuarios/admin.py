from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'full_name', 'email', 'rol_icon', 'cedula', 'is_active', 'date_joined')
    list_filter = ('rol', 'is_active', 'date_joined', 'last_login')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'cedula')
    ordering = ('username',)

    fieldsets = UserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': ('rol', 'cedula', 'telegram_id'),
            'description': 'Información específica del sistema académico'
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('rol', 'cedula', 'email', 'first_name', 'last_name'),
            'description': 'Complete la información básica del usuario'
        }),
    )

    def full_name(self, obj):
        return obj.get_full_name() or obj.username
    full_name.short_description = 'Nombre Completo'

    def rol_icon(self, obj):
        icons = {
            'estudiante': '👨‍🎓',
            'docente': '👨‍🏫',
            'director': '👨‍💼',
            'administrador': '⚙️',
        }
        icon = icons.get(obj.rol, '👤')
        return f"{icon} {obj.get_rol_display()}"
    rol_icon.short_description = 'Rol'

    actions = ['activar_usuarios', 'desactivar_usuarios', 'enviar_credenciales']

    def activar_usuarios(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"Se activaron {count} usuarios")
    activar_usuarios.short_description = "Activar usuarios seleccionados"

    def desactivar_usuarios(self, request, queryset):
        count = queryset.filter(is_superuser=False).update(is_active=False)
        self.message_user(request, f"Se desactivaron {count} usuarios (superusuarios no afectados)")
    desactivar_usuarios.short_description = "Desactivar usuarios seleccionados"

    def enviar_credenciales(self, request, queryset):
        # Placeholder para funcionalidad de envío de credenciales
        count = queryset.count()
        self.message_user(request, f"Funcionalidad de envío de credenciales para {count} usuarios en desarrollo")
    enviar_credenciales.short_description = "Enviar credenciales por email"