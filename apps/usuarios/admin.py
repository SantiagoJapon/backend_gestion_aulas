from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'rol', 'is_active')
    list_filter = ('rol', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'cedula')

    fieldsets = UserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': ('rol', 'cedula', 'telegram_id')
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('rol', 'cedula', 'email', 'first_name', 'last_name')
        }),
    )