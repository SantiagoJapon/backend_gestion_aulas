# apps/planificacion/tasks.py
from celery import shared_task
from django.shortcuts import get_object_or_404
import pandas as pd
from datetime import datetime, time
import logging
from .models import PlanificacionAcademica, ClasePlanificada, Materia
from apps.usuarios.models import CustomUser
from apps.aulas.models import TipoAula
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'apps'))

logger = logging.getLogger(__name__)

def validar_columnas(df, columnas_requeridas):
    columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
    return columnas_faltantes

def obtener_docente(row, planificacion, index):
    from apps.usuarios.models import CustomUser
    docente_nombres = row['docente'].split()
    docente = None
    if len(docente_nombres) >= 2:
        docente = CustomUser.objects.filter(
            first_name__icontains=docente_nombres[0],
            last_name__icontains=docente_nombres[-1],
            rol='docente'
        ).first()
    if not docente:
        docente = CustomUser.objects.create_user(
            username=f"doc_{row['codigo_materia']}_{index}",
            first_name=docente_nombres[0] if docente_nombres else "Nombre",
            last_name=" ".join(docente_nombres[1:]) if len(docente_nombres) > 1 else "Apellido",
            rol='docente',
            carrera=planificacion.carrera
        )
    return docente

@shared_task
def procesar_planificacion_task(planificacion_id):
    """Tarea para procesar archivo de planificación de forma asíncrona"""
    try:
        planificacion = get_object_or_404(PlanificacionAcademica, id=planificacion_id)
        planificacion.estado = 'procesando'
        planificacion.save()
        
        df = pd.read_excel(planificacion.archivo_planificacion.path)
        columnas_requeridas = [
            'codigo_materia', 'nombre_materia', 'docente', 'paralelo',
            'numero_estudiantes', 'dia_semana', 'hora_inicio', 'hora_fin',
            'tipo_aula', 'creditos', 'nivel'
        ]
        columnas_faltantes = validar_columnas(df, columnas_requeridas)
        if columnas_faltantes:
            planificacion.estado = 'con_conflictos'
            planificacion.observaciones = f'Faltan columnas: {", ".join(columnas_faltantes)}'
            planificacion.save()
            return False
        
        clases_procesadas = 0
        errores = []
        
        for index, row in df.iterrows():
            try:
                tipo_aula, _ = TipoAula.objects.get_or_create(nombre=row['tipo_aula'])
                materia, _ = Materia.objects.get_or_create(
                    codigo=row['codigo_materia'],
                    defaults={
                        'nombre': row['nombre_materia'],
                        'creditos': row['creditos'],
                        'carrera': planificacion.carrera,
                        'nivel': row['nivel'],
                        'tipo_aula_requerida': tipo_aula
                    }
                )
                docente = obtener_docente(row, planificacion, index)
                hora_inicio = datetime.strptime(str(row['hora_inicio']), '%H:%M').time() if isinstance(row['hora_inicio'], str) else row['hora_inicio']
                hora_fin = datetime.strptime(str(row['hora_fin']), '%H:%M').time() if isinstance(row['hora_fin'], str) else row['hora_fin']
                ClasePlanificada.objects.create(
                    planificacion=planificacion,
                    materia=materia,
                    docente=docente,
                    paralelo=str(row['paralelo']),
                    numero_estudiantes=int(row['numero_estudiantes']),
                    dia_semana=row['dia_semana'].lower(),
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    tipo_clase=row.get('tipo_clase', 'Teórica')
                )
                clases_procesadas += 1
            except Exception as e:
                error_msg = f"Error en fila {index + 1}: {str(e)}"
                errores.append(error_msg)
                logger.error(error_msg)
        
        if errores:
            planificacion.estado = 'con_conflictos'
            planificacion.observaciones = f"Procesadas {clases_procesadas} clases. Errores: {'; '.join(errores[:5])}"
        else:
            planificacion.estado = 'asignada'
            planificacion.observaciones = f"Procesadas {clases_procesadas} clases exitosamente"
        planificacion.save()
        asignar_aulas_automaticamente_task.delay(planificacion_id)
        return True
        
    except Exception as e:
        logger.error(f"Error procesando planificación {planificacion_id}: {str(e)}")
        planificacion = get_object_or_404(PlanificacionAcademica, id=planificacion_id)
        planificacion.estado = 'con_conflictos'
        planificacion.observaciones = f"Error crítico: {str(e)}"
        planificacion.save()
        return False

@shared_task
def asignar_aulas_automaticamente_task(planificacion_id):
    """Tarea para asignar aulas automáticamente usando algoritmo inteligente"""
    from apps.asignaciones.models import AsignacionAula, ConflictoHorario
    from apps.aulas.models import Aula
    
    try:
        planificacion = get_object_or_404(PlanificacionAcademica, id=planificacion_id)
        clases_planificadas = ClasePlanificada.objects.filter(planificacion=planificacion)
        
        asignaciones_exitosas = 0
        conflictos_detectados = 0
        
        for clase in clases_planificadas:
            # Buscar aulas compatibles
            aulas_compatibles = Aula.objects.filter(
                tipo=clase.materia.tipo_aula_requerida,
                capacidad__gte=clase.numero_estudiantes,
                is_disponible=True
            ).order_by('capacidad')  # Priorizar aulas con capacidad justa
            
            aula_asignada = None
            
            for aula in aulas_compatibles:
                # Verificar conflictos de horario
                conflicto = AsignacionAula.objects.filter(
                    aula=aula,
                    clase_planificada__dia_semana=clase.dia_semana,
                    clase_planificada__hora_inicio__lt=clase.hora_fin,
                    clase_planificada__hora_fin__gt=clase.hora_inicio,
                    estado__in=['asignada', 'confirmada']
                ).exists()
                
                if not conflicto:
                    # Asignar aula
                    AsignacionAula.objects.create(
                        clase_planificada=clase,
                        aula=aula,
                        estado='asignada',
                        prioridad=1
                    )
                    aula_asignada = aula
                    asignaciones_exitosas += 1
                    break
            
            if not aula_asignada:
                # Registrar conflicto
                tipo_conflicto = 'aula_ocupada' if aulas_compatibles.exists() else 'capacidad_insuficiente'
                ConflictoHorario.objects.create(
                    clase_planificada=clase,
                    tipo_conflicto=tipo_conflicto,
                    descripcion=f"No se encontró aula disponible para {clase.materia.nombre} - {clase.paralelo}",
                    estado='detectado'
                )
                conflictos_detectados += 1
        
        # Actualizar observaciones de la planificación
        observaciones = f"Asignación automática completada. {asignaciones_exitosas} aulas asignadas, {conflictos_detectados} conflictos detectados."
        planificacion.observaciones += f" {observaciones}"
        planificacion.save()
        
        logger.info(f"Asignación completada para planificación {planificacion_id}: {observaciones}")
        return True
        
    except Exception as e:
        logger.error(f"Error en asignación automática {planificacion_id}: {str(e)}")
        return False
