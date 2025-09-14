"""
Comando Django para generar horarios automáticamente
Usage: python manage.py generate_schedule --planificacion <id> --strategy <strategy>
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.planificacion.models import PlanificacionAcademica
from apps.planificacion.scheduling.base import SchedulingStrategy
from apps.planificacion.scheduling.strategies import SchedulingEngineFactory
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Genera horarios automáticamente para una planificación académica'

    def add_arguments(self, parser):
        parser.add_argument(
            '--planificacion',
            type=int,
            required=True,
            help='ID de la planificación académica'
        )

        parser.add_argument(
            '--strategy',
            type=str,
            choices=[s.value for s in SchedulingStrategy],
            default=SchedulingStrategy.DOCENTE_PRIORITY.value,
            help='Estrategia de planificación a utilizar'
        )

        parser.add_argument(
            '--save',
            action='store_true',
            help='Guardar los resultados en la base de datos'
        )

        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada del proceso'
        )

        # Parámetros específicos para algoritmo genético
        parser.add_argument(
            '--population-size',
            type=int,
            default=50,
            help='Tamaño de población para algoritmo genético'
        )

        parser.add_argument(
            '--generations',
            type=int,
            default=100,
            help='Número de generaciones para algoritmo genético'
        )

        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar simulación sin guardar cambios'
        )

    def handle(self, *args, **options):
        planificacion_id = options['planificacion']
        strategy_name = options['strategy']
        save_results = options['save']
        verbose = options['verbose']
        dry_run = options['dry_run']

        # Configurar logging
        if verbose:
            logging.basicConfig(level=logging.INFO)

        try:
            # Obtener planificación
            planificacion = PlanificacionAcademica.objects.get(id=planificacion_id)
            self.stdout.write(
                self.style.SUCCESS(f'Planificacion: {planificacion.nombre}')
            )

            # Validar que la planificación esté en estado apropiado
            if planificacion.estado not in ['borrador', 'revision']:
                raise CommandError(
                    f'La planificación debe estar en estado "borrador" o "revision", '
                    f'actual: {planificacion.get_estado_display()}'
                )

            # Crear estrategia
            strategy = SchedulingStrategy(strategy_name)
            self.stdout.write(f'Estrategia: {strategy.value}')

            # Parámetros adicionales
            engine_params = {}
            if strategy == SchedulingStrategy.GENETIC_ALGORITHM:
                engine_params['population_size'] = options['population_size']
                engine_params['generations'] = options['generations']
                self.stdout.write(
                    f'Parametros GA: poblacion={engine_params["population_size"]}, '
                    f'generaciones={engine_params["generations"]}'
                )

            # Crear motor de planificación
            engine = SchedulingEngineFactory.create_engine(strategy, **engine_params)

            self.stdout.write('Iniciando generacion de horarios...')
            start_time = timezone.now()

            # Ejecutar planificación
            result = engine.execute_scheduling(planificacion)

            execution_time = (timezone.now() - start_time).total_seconds()

            # Mostrar resultados
            self._display_results(result, execution_time)

            # Guardar si se solicita y no es dry-run
            if save_results and not dry_run:
                self.stdout.write('Guardando resultados...')

                saved = engine.save_scheduling_result(planificacion, result)

                if saved:
                    self.stdout.write(
                        self.style.SUCCESS('Horarios guardados exitosamente')
                    )

                    # Actualizar estado de planificación si fue exitosa
                    if result.success and planificacion.estado == 'borrador':
                        planificacion.estado = 'revision'
                        planificacion.save()
                        self.stdout.write('Planificacion marcada como "En Revision"')
                else:
                    self.stdout.write(
                        self.style.ERROR('Error guardando horarios')
                    )
            elif dry_run:
                self.stdout.write(
                    self.style.WARNING('Simulacion completada (no se guardaron cambios)')
                )

        except PlanificacionAcademica.DoesNotExist:
            raise CommandError(f'Planificación con ID {planificacion_id} no encontrada')

        except Exception as e:
            raise CommandError(f'Error ejecutando planificación: {str(e)}')

    def _display_results(self, result, execution_time):
        """Muestra los resultados de la planificación"""

        # Encabezado de resultados
        self.stdout.write('\n' + '='*50)
        self.stdout.write('RESULTADOS DE PLANIFICACION')
        self.stdout.write('='*50)

        # Estado general
        if result.success:
            self.stdout.write(self.style.SUCCESS('Estado: EXITOSO'))
        else:
            self.stdout.write(self.style.ERROR('Estado: CON CONFLICTOS'))

        # Estadísticas básicas
        self.stdout.write(f'Tiempo de ejecucion: {execution_time:.2f} segundos')
        self.stdout.write(f'Estrategia utilizada: {result.strategy_used.value}')
        self.stdout.write(f'Puntuacion total: {result.score:.2f}')

        # Asignaciones creadas
        self.stdout.write(f'\nAsignaciones de horario:')
        self.stdout.write(f'   Creadas: {len(result.assignments)}')
        self.stdout.write(f'   No asignadas: {len(result.unassigned)}')

        if result.assignments:
            self.stdout.write('\nDetalle de asignaciones creadas:')
            for i, assignment in enumerate(result.assignments[:10], 1):  # Mostrar primeras 10
                docente = assignment.asignacion_docente.docente.get_full_name()
                materia = assignment.asignacion_docente.materia.nombre
                franja = assignment.franja_horaria
                aula = assignment.aula.codigo
                score = assignment.score

                self.stdout.write(
                    f'   {i:2}. {materia[:30]:30} | {docente[:20]:20} | '
                    f'{franja.get_dia_semana_display()} {franja.hora_inicio} | '
                    f'{aula} | Score: {score:.1f}'
                )

            if len(result.assignments) > 10:
                self.stdout.write(f'   ... y {len(result.assignments) - 10} más')

        # Conflictos detectados
        if result.conflicts:
            self.stdout.write(f'\nConflictos detectados: {len(result.conflicts)}')
            for i, conflict in enumerate(result.conflicts[:5], 1):  # Mostrar primeros 5
                self.stdout.write(f'   {i}. {conflict.descripcion[:80]}')

            if len(result.conflicts) > 5:
                self.stdout.write(f'   ... y {len(result.conflicts) - 5} conflictos más')

        # Asignaciones no realizadas
        if result.unassigned:
            self.stdout.write(f'\nAsignaciones no realizadas: {len(result.unassigned)}')
            for i, unassigned in enumerate(result.unassigned[:5], 1):
                docente = unassigned.docente.get_full_name()
                materia = unassigned.materia.nombre
                self.stdout.write(f'   {i}. {materia} - {docente}')

            if len(result.unassigned) > 5:
                self.stdout.write(f'   ... y {len(result.unassigned) - 5} más')

        # Mensaje del resultado
        if result.message:
            self.stdout.write(f'\n{result.message}')

        self.stdout.write('='*50 + '\n')

    def _show_available_strategies(self):
        """Muestra las estrategias disponibles"""
        strategies = SchedulingEngineFactory.get_available_strategies()

        self.stdout.write('\nEstrategias de planificacion disponibles:')
        self.stdout.write('-' * 50)

        for strategy in strategies:
            self.stdout.write(f"- {strategy['key']}")
            self.stdout.write(f"   Nombre: {strategy['name']}")
            self.stdout.write(f"   Descripción: {strategy['description']}")
            self.stdout.write('')