#!/usr/bin/env python
"""
Script para ejecutar migraciones con configuración de encoding mejorada
"""
import os
import sys
import locale
import codecs

# Configurar encoding antes de cualquier import de Django
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

# Variables de entorno
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PGCLIENTENCODING'] = 'UTF8'
os.environ['LC_ALL'] = 'C.UTF-8'
os.environ['LANG'] = 'C.UTF-8'

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horarios_backend.settings_postgresql')

    try:
        from django.core.management import execute_from_command_line

        print("🔄 Ejecutando migraciones en PostgreSQL...")
        print(f"🌐 Encoding del sistema: {locale.getpreferredencoding()}")

        # Ejecutar migraciones
        execute_from_command_line(['run_migrations.py', 'migrate', '--verbosity=2'])

        print("✅ Migraciones completadas exitosamente!")

    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Está instalado y "
            "disponible en tu PYTHONPATH? ¿Olvidaste activar el entorno virtual?"
        ) from exc
    except Exception as e:
        print(f"❌ Error durante las migraciones: {e}")
        raise

if __name__ == '__main__':
    main()