#!/usr/bin/env python
"""
Script para crear datos de prueba para el sistema de planificación académica
"""
import os
import sys
import django
from datetime import date, time, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horarios_backend.settings_dev')
django.setup()

from apps.usuarios.models import CustomUser
from apps.aulas.models import Aula, TipoAula
from apps.planificacion.models import Carrera, Periodo, Materia, FranjaHoraria, PlanificacionAcademica
from apps.asignaciones.models import AsignacionDocente, HorarioClase


def crear_usuarios():
    print("Creando usuarios...")

    # Admin
    admin, created = CustomUser.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@universidad.edu',
            'first_name': 'Administrador',
            'last_name': 'Sistema',
            'rol': 'administrador',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin.set_password('admin123')
        admin.save()

    # Director
    director, created = CustomUser.objects.get_or_create(
        username='director',
        defaults={
            'email': 'director@universidad.edu',
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'rol': 'director',
            'is_staff': True
        }
    )
    if created:
        director.set_password('director123')
        director.save()

    # Docentes
    docentes_data = [
        ('docente1', 'María', 'González', 'maria.gonzalez@universidad.edu'),
        ('docente2', 'Carlos', 'Rodríguez', 'carlos.rodriguez@universidad.edu'),
        ('docente3', 'Ana', 'López', 'ana.lopez@universidad.edu'),
        ('docente4', 'Luis', 'Martínez', 'luis.martinez@universidad.edu'),
    ]

    docentes = []
    for username, first_name, last_name, email in docentes_data:
        docente, created = CustomUser.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'rol': 'docente'
            }
        )
        if created:
            docente.set_password('docente123')
            docente.save()
        docentes.append(docente)

    # Estudiantes
    estudiantes_data = [
        ('estudiante1', 'Pedro', 'García', 'pedro.garcia@estudiantes.edu'),
        ('estudiante2', 'Sofía', 'Hernández', 'sofia.hernandez@estudiantes.edu'),
        ('estudiante3', 'Diego', 'Torres', 'diego.torres@estudiantes.edu'),
    ]

    estudiantes = []
    for username, first_name, last_name, email in estudiantes_data:
        estudiante, created = CustomUser.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'rol': 'estudiante'
            }
        )
        if created:
            estudiante.set_password('estudiante123')
            estudiante.save()
        estudiantes.append(estudiante)

    return admin, director, docentes, estudiantes


def crear_carreras_y_materias():
    print("Creando carreras y materias...")

    # Carreras
    carreras_data = [
        ('ISW', 'Ingeniería en Software', 'Carrera de ingeniería enfocada en desarrollo de software', 8),
        ('IEC', 'Ingeniería Electrónica', 'Carrera de ingeniería en sistemas electrónicos', 10),
        ('IGI', 'Ingeniería en Gestión de la Información', 'Carrera enfocada en gestión de datos e información', 8),
    ]

    carreras = []
    for codigo, nombre, descripcion, semestres in carreras_data:
        carrera, created = Carrera.objects.get_or_create(
            codigo=codigo,
            defaults={
                'nombre': nombre,
                'descripcion': descripcion,
                'duracion_semestres': semestres
            }
        )
        carreras.append(carrera)

    # Materias para Ingeniería en Software
    isw_materias = [
        ('MAT101', 'Matemáticas I', 'Álgebra y cálculo diferencial', 4, 6, 1),
        ('FIS101', 'Física I', 'Mecánica y termodinámica', 3, 4, 1),
        ('PRG101', 'Programación I', 'Introducción a la programación', 4, 6, 1),
        ('PRG102', 'Programación II', 'Programación orientada a objetos', 4, 6, 2),
        ('BDD101', 'Base de Datos I', 'Diseño y gestión de bases de datos', 3, 4, 3),
        ('ING101', 'Ingeniería de Software', 'Metodologías de desarrollo', 4, 6, 4),
    ]

    materias = []
    for codigo, nombre, descripcion, creditos, horas, semestre in isw_materias:
        materia, created = Materia.objects.get_or_create(
            codigo=codigo,
            defaults={
                'nombre': nombre,
                'descripcion': descripcion,
                'creditos': creditos,
                'horas_semanales': horas,
                'semestre': semestre,
                'carrera': carreras[0]  # ISW
            }
        )
        materias.append(materia)

    # Establecer prerequisitos
    if len(materias) >= 4:
        materias[3].prereq_materias.add(materias[2])  # PRG102 requiere PRG101

    return carreras, materias


def crear_periodo_y_franjas():
    print("Creando períodos y franjas horarias...")

    # Período actual
    periodo, created = Periodo.objects.get_or_create(
        anio=2024,
        numero=2,
        tipo='semestre',
        defaults={
            'nombre': '2do Semestre',
            'fecha_inicio': date(2024, 9, 1),
            'fecha_fin': date(2025, 1, 31),
            'is_activo': True
        }
    )

    # Franjas horarias
    franjas_data = [
        ('1era Hora', 'lunes', time(7, 0), time(8, 30)),
        ('2da Hora', 'lunes', time(8, 30), time(10, 0)),
        ('3era Hora', 'lunes', time(10, 30), time(12, 0)),
        ('1era Hora', 'martes', time(7, 0), time(8, 30)),
        ('2da Hora', 'martes', time(8, 30), time(10, 0)),
        ('3era Hora', 'martes', time(10, 30), time(12, 0)),
        ('1era Hora', 'miercoles', time(7, 0), time(8, 30)),
        ('2da Hora', 'miercoles', time(8, 30), time(10, 0)),
        ('1era Hora', 'jueves', time(7, 0), time(8, 30)),
        ('2da Hora', 'jueves', time(8, 30), time(10, 0)),
        ('1era Hora', 'viernes', time(7, 0), time(8, 30)),
        ('2da Hora', 'viernes', time(8, 30), time(10, 0)),
    ]

    franjas = []
    for nombre, dia, inicio, fin in franjas_data:
        franja, created = FranjaHoraria.objects.get_or_create(
            nombre=nombre,
            dia_semana=dia,
            hora_inicio=inicio,
            hora_fin=fin
        )
        franjas.append(franja)

    return periodo, franjas


def crear_planificacion_y_asignaciones(admin, carreras, materias, periodo, docentes, franjas):
    print("Creando planificación académica...")

    # Planificación
    planificacion, created = PlanificacionAcademica.objects.get_or_create(
        nombre='Planificación 2do Semestre 2024',
        periodo=periodo,
        defaults={
            'estado': 'vigente',
            'creado_por': admin,
            'aprobado_por': admin,
            'observaciones': 'Planificación de prueba para el sistema'
        }
    )

    if created:
        planificacion.carreras.add(carreras[0])  # Agregar ISW

    # Asignaciones de docentes
    asignaciones_data = [
        (docentes[0], materias[0], 6),  # María - Matemáticas I
        (docentes[1], materias[1], 4),  # Carlos - Física I
        (docentes[2], materias[2], 6),  # Ana - Programación I
        (docentes[3], materias[3], 6),  # Luis - Programación II
    ]

    asignaciones = []
    for docente, materia, horas in asignaciones_data:
        asignacion, created = AsignacionDocente.objects.get_or_create(
            docente=docente,
            materia=materia,
            planificacion=planificacion,
            defaults={
                'carga_horaria_semanal': horas,
                'observaciones': f'Asignación de {materia.nombre} a {docente.get_full_name()}'
            }
        )
        asignaciones.append(asignacion)

    # Horarios de clase
    if len(asignaciones) >= 2 and len(franjas) >= 4:
        # Obtener aulas existentes
        aulas = list(Aula.objects.all()[:2])  # Tomar las primeras 2 aulas

        if aulas:
            horarios_data = [
                (asignaciones[0], franjas[0], aulas[0], 25),  # Matemáticas - Lunes 7:00
                (asignaciones[1], franjas[1], aulas[1], 20),  # Física - Lunes 8:30
                (asignaciones[2], franjas[3], aulas[0], 30),  # Prog I - Martes 7:00
                (asignaciones[3], franjas[4], aulas[1], 25),  # Prog II - Martes 8:30
            ]

            horarios = []
            for asignacion, franja, aula, capacidad in horarios_data:
                horario, created = HorarioClase.objects.get_or_create(
                    asignacion_docente=asignacion,
                    franja_horaria=franja,
                    aula=aula,
                    defaults={
                        'capacidad_estudiantes': capacidad,
                        'modalidad': 'presencial',
                        'observaciones': f'Clase de {asignacion.materia.nombre}'
                    }
                )
                horarios.append(horario)

            return planificacion, asignaciones, horarios

    return planificacion, asignaciones, []


def main():
    print("Creando datos de prueba para el sistema de planificacion...")

    try:
        # Crear usuarios
        admin, director, docentes, estudiantes = crear_usuarios()
        print(f"OK - Usuarios creados: 1 admin, 1 director, {len(docentes)} docentes, {len(estudiantes)} estudiantes")

        # Crear carreras y materias
        carreras, materias = crear_carreras_y_materias()
        print(f"OK - Creadas: {len(carreras)} carreras, {len(materias)} materias")

        # Crear período y franjas
        periodo, franjas = crear_periodo_y_franjas()
        print(f"OK - Creado: 1 periodo, {len(franjas)} franjas horarias")

        # Crear planificación y asignaciones
        planificacion, asignaciones, horarios = crear_planificacion_y_asignaciones(
            admin, carreras, materias, periodo, docentes, franjas
        )
        print(f"OK - Creadas: 1 planificacion, {len(asignaciones)} asignaciones, {len(horarios)} horarios")

        print(f"""
EXITO - Datos de prueba creados correctamente!

Resumen:
- Usuarios: {1 + 1 + len(docentes) + len(estudiantes)}
- Carreras: {len(carreras)}
- Materias: {len(materias)}
- Franjas horarias: {len(franjas)}
- Asignaciones: {len(asignaciones)}
- Horarios de clase: {len(horarios)}

Credenciales de acceso:
- Admin: admin/admin123
- Director: director/director123
- Docentes: docente1/docente123, docente2/docente123, etc.
- Estudiantes: estudiante1/estudiante123, etc.
        """)

    except Exception as e:
        print(f"ERROR - Error creando datos de prueba: {e}")
        return False

    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)