"""
Implementaciones específicas de estrategias de planificación automática
"""

import random
from typing import List, Dict, Set
from django.db.models import Count, Q
from .base import BaseSchedulingEngine, SchedulingAssignment, SchedulingStrategy
from ..models import PlanificacionAcademica, FranjaHoraria
from apps.asignaciones.models import AsignacionDocente, HorarioClase
from apps.aulas.models import Aula
import logging

logger = logging.getLogger(__name__)


class DocentePriorityEngine(BaseSchedulingEngine):
    """
    Estrategia que prioriza las preferencias y disponibilidad de los docentes
    """

    def __init__(self):
        super().__init__(SchedulingStrategy.DOCENTE_PRIORITY)

    def generate_assignments(self, planificacion: PlanificacionAcademica) -> List[SchedulingAssignment]:
        """Genera asignaciones priorizando docentes"""
        assignments = []

        # Obtener todas las asignaciones docente-materia
        asignaciones = AsignacionDocente.objects.filter(
            planificacion=planificacion,
            is_activa=True
        ).select_related('docente', 'materia').order_by('docente__last_name')

        # Obtener franjas horarias disponibles
        franjas = list(FranjaHoraria.objects.filter(is_activa=True).order_by('dia_semana', 'hora_inicio'))

        # Obtener aulas disponibles
        aulas = list(Aula.objects.filter(is_disponible=True).order_by('capacidad'))

        # Tracking de asignaciones por docente y franja
        docente_franjas_usadas = {}
        aula_franjas_usadas = set()

        for asignacion in asignaciones:
            docente_id = asignacion.docente.id
            if docente_id not in docente_franjas_usadas:
                docente_franjas_usadas[docente_id] = set()

            # Buscar la mejor franja y aula para esta asignación
            best_assignment = None
            best_score = -1

            for franja in franjas:
                # Skip si el docente ya tiene clase en esta franja
                if franja.id in docente_franjas_usadas[docente_id]:
                    continue

                for aula in aulas:
                    # Skip si el aula ya está ocupada en esta franja
                    if (aula.id, franja.id) in aula_franjas_usadas:
                        continue

                    # Calcular capacidad apropiada (80% de la capacidad del aula)
                    capacidad_estudiantes = min(30, int(aula.capacidad * 0.8))

                    assignment = SchedulingAssignment(
                        asignacion_docente=asignacion,
                        franja_horaria=franja,
                        aula=aula,
                        capacidad_estudiantes=capacidad_estudiantes,
                        modalidad='presencial'
                    )

                    # Calcular score para esta combinación
                    score = self._calculate_docente_priority_score(assignment, asignaciones)

                    if score > best_score:
                        best_score = score
                        best_assignment = assignment

            if best_assignment:
                # Marcar como usado
                docente_franjas_usadas[docente_id].add(best_assignment.franja_horaria.id)
                aula_franjas_usadas.add((best_assignment.aula.id, best_assignment.franja_horaria.id))

                best_assignment.score = best_score
                assignments.append(best_assignment)

        logger.info(f"DocentePriority generó {len(assignments)} asignaciones de {len(asignaciones)} solicitadas")
        return assignments

    def _calculate_docente_priority_score(self, assignment: SchedulingAssignment,
                                        all_asignaciones: List[AsignacionDocente]) -> float:
        """Calcula score basado en prioridades del docente"""
        score = 100.0

        # Bonificación por horarios matutinos (preferidos generalmente)
        if assignment.franja_horaria.hora_inicio.hour < 10:
            score += 20

        # Bonificación por distribución equilibrada en la semana
        dia_semana = assignment.franja_horaria.dia_semana
        if dia_semana in ['martes', 'miercoles', 'jueves']:  # Días medios preferidos
            score += 15

        # Penalización por aulas muy grandes para grupos pequeños (desperdicio)
        if assignment.aula.capacidad > assignment.capacidad_estudiantes * 2:
            score -= 10

        # Bonificación por tipo de aula apropiado
        materia_nombre = assignment.asignacion_docente.materia.nombre.lower()
        aula_tipo = assignment.aula.tipo.nombre.lower()

        if 'laboratorio' in materia_nombre and 'laboratorio' in aula_tipo:
            score += 30
        elif 'laboratorio' not in materia_nombre and 'magistral' in aula_tipo:
            score += 20

        return score


class AulaOptimizationEngine(BaseSchedulingEngine):
    """
    Estrategia que optimiza el uso eficiente de las aulas
    """

    def __init__(self):
        super().__init__(SchedulingStrategy.AULA_OPTIMIZATION)

    def generate_assignments(self, planificacion: PlanificacionAcademica) -> List[SchedulingAssignment]:
        """Genera asignaciones optimizando uso de aulas"""
        assignments = []

        # Obtener asignaciones ordenadas por capacidad requerida (descendente)
        asignaciones = AsignacionDocente.objects.filter(
            planificacion=planificacion,
            is_activa=True
        ).select_related('docente', 'materia').order_by('-materia__horas_semanales')

        # Obtener aulas ordenadas por capacidad
        aulas = list(Aula.objects.filter(is_disponible=True).order_by('capacidad'))
        franjas = list(FranjaHoraria.objects.filter(is_activa=True).order_by('dia_semana', 'hora_inicio'))

        # Tracking de uso de recursos
        aula_ocupacion = {aula.id: [] for aula in aulas}
        docente_horarios = {}

        for asignacion in asignaciones:
            # Estimar capacidad requerida basada en la materia
            capacidad_requerida = self._estimate_capacity_needed(asignacion)

            best_assignment = None
            best_efficiency = -1

            for aula in aulas:
                if aula.capacidad < capacidad_requerida:
                    continue  # Aula muy pequeña

                for franja in franjas:
                    # Verificar disponibilidad
                    if self._is_aula_available(aula, franja, aula_ocupacion):
                        if self._is_docente_available(asignacion.docente, franja, docente_horarios):

                            assignment = SchedulingAssignment(
                                asignacion_docente=asignacion,
                                franja_horaria=franja,
                                aula=aula,
                                capacidad_estudiantes=capacidad_requerida,
                                modalidad='presencial'
                            )

                            # Calcular eficiencia de uso del aula
                            efficiency = self._calculate_aula_efficiency(assignment)

                            if efficiency > best_efficiency:
                                best_efficiency = efficiency
                                best_assignment = assignment

            if best_assignment:
                # Marcar recursos como usados
                aula_id = best_assignment.aula.id
                franja_id = best_assignment.franja_horaria.id
                docente_id = best_assignment.asignacion_docente.docente.id

                aula_ocupacion[aula_id].append(franja_id)

                if docente_id not in docente_horarios:
                    docente_horarios[docente_id] = []
                docente_horarios[docente_id].append(franja_id)

                best_assignment.score = best_efficiency
                assignments.append(best_assignment)

        logger.info(f"AulaOptimization generó {len(assignments)} asignaciones")
        return assignments

    def _estimate_capacity_needed(self, asignacion: AsignacionDocente) -> int:
        """Estima la capacidad de estudiantes necesaria"""
        # Lógica básica - se puede mejorar con datos históricos
        base_capacity = 25

        # Ajustar según el semestre de la materia
        if asignacion.materia.semestre <= 2:
            return base_capacity + 10  # Semestres iniciales más concurridos
        elif asignacion.materia.semestre >= 7:
            return base_capacity - 5   # Semestres avanzados menos concurridos

        return base_capacity

    def _is_aula_available(self, aula: Aula, franja: FranjaHoraria, ocupacion: Dict) -> bool:
        """Verifica si un aula está disponible en una franja"""
        return franja.id not in ocupacion[aula.id]

    def _is_docente_available(self, docente, franja: FranjaHoraria, horarios: Dict) -> bool:
        """Verifica si un docente está disponible en una franja"""
        return docente.id not in horarios or franja.id not in horarios[docente.id]

    def _calculate_aula_efficiency(self, assignment: SchedulingAssignment) -> float:
        """Calcula la eficiencia de uso del aula"""
        aula_capacity = assignment.aula.capacidad
        needed_capacity = assignment.capacidad_estudiantes

        # Eficiencia = qué tan bien se usa el aula (cerca del 80% es ideal)
        usage_ratio = needed_capacity / aula_capacity

        if 0.6 <= usage_ratio <= 0.9:  # Uso óptimo
            efficiency = 100
        elif usage_ratio < 0.6:  # Subutilizada
            efficiency = 50 + (usage_ratio * 50)
        else:  # Sobrecargada
            efficiency = 90 - ((usage_ratio - 0.9) * 100)

        # Bonificación por tipo de aula apropiado
        materia_nombre = assignment.asignacion_docente.materia.nombre.lower()
        aula_tipo = assignment.aula.tipo.nombre.lower()

        if ('laboratorio' in materia_nombre and 'laboratorio' in aula_tipo) or \
           ('laboratorio' not in materia_nombre and 'magistral' in aula_tipo):
            efficiency += 20

        return efficiency


class BalancedDistributionEngine(BaseSchedulingEngine):
    """
    Estrategia que busca una distribución equilibrada de la carga horaria
    """

    def __init__(self):
        super().__init__(SchedulingStrategy.BALANCED_DISTRIBUTION)

    def generate_assignments(self, planificacion: PlanificacionAcademica) -> List[SchedulingAssignment]:
        """Genera asignaciones con distribución equilibrada"""
        assignments = []

        asignaciones = list(AsignacionDocente.objects.filter(
            planificacion=planificacion,
            is_activa=True
        ).select_related('docente', 'materia'))

        franjas = list(FranjaHoraria.objects.filter(is_activa=True).order_by('dia_semana', 'hora_inicio'))
        aulas = list(Aula.objects.filter(is_disponible=True))

        # Agrupar franjas por día para distribución equilibrada
        franjas_por_dia = {}
        for franja in franjas:
            dia = franja.dia_semana
            if dia not in franjas_por_dia:
                franjas_por_dia[dia] = []
            franjas_por_dia[dia].append(franja)

        # Tracking de distribución
        ocupacion_por_dia = {dia: 0 for dia in franjas_por_dia.keys()}
        recursos_usados = set()  # (docente_id, franja_id) y (aula_id, franja_id)

        # Distribuir asignaciones de manera equilibrada
        dias_disponibles = list(franjas_por_dia.keys())

        for i, asignacion in enumerate(asignaciones):
            # Seleccionar día con menos carga
            dia_seleccionado = min(ocupacion_por_dia.keys(), key=lambda d: ocupacion_por_dia[d])

            best_assignment = None
            best_score = -1

            for franja in franjas_por_dia[dia_seleccionado]:
                # Verificar disponibilidad del docente
                if (asignacion.docente.id, franja.id) in recursos_usados:
                    continue

                for aula in aulas:
                    # Verificar disponibilidad del aula
                    if (aula.id, franja.id) in recursos_usados:
                        continue

                    capacidad = min(30, int(aula.capacidad * 0.8))

                    assignment = SchedulingAssignment(
                        asignacion_docente=asignacion,
                        franja_horaria=franja,
                        aula=aula,
                        capacidad_estudiantes=capacidad,
                        modalidad='presencial'
                    )

                    score = self._calculate_balance_score(assignment, ocupacion_por_dia)

                    if score > best_score:
                        best_score = score
                        best_assignment = assignment

            if best_assignment:
                # Actualizar contadores
                dia = best_assignment.franja_horaria.dia_semana
                ocupacion_por_dia[dia] += 1

                recursos_usados.add((best_assignment.asignacion_docente.docente.id, best_assignment.franja_horaria.id))
                recursos_usados.add((best_assignment.aula.id, best_assignment.franja_horaria.id))

                best_assignment.score = best_score
                assignments.append(best_assignment)

        logger.info(f"BalancedDistribution generó {len(assignments)} asignaciones")
        return assignments

    def _calculate_balance_score(self, assignment: SchedulingAssignment, ocupacion_por_dia: Dict) -> float:
        """Calcula score basado en equilibrio de distribución"""
        score = 100.0

        # Penalizar días con mucha carga
        dia = assignment.franja_horaria.dia_semana
        carga_actual = ocupacion_por_dia[dia]

        if carga_actual == 0:  # Primer horario del día
            score += 30
        elif carga_actual <= 2:  # Carga baja
            score += 20
        elif carga_actual <= 4:  # Carga media
            score += 10
        else:  # Carga alta
            score -= 20

        # Bonificar horarios intermedios del día
        hora = assignment.franja_horaria.hora_inicio.hour
        if 8 <= hora <= 11:
            score += 15
        elif 14 <= hora <= 16:
            score += 10

        return score


class GeneticAlgorithmEngine(BaseSchedulingEngine):
    """
    Estrategia avanzada usando algoritmo genético para optimización global
    """

    def __init__(self, population_size: int = 50, generations: int = 100):
        super().__init__(SchedulingStrategy.GENETIC_ALGORITHM)
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = 0.1

    def generate_assignments(self, planificacion: PlanificacionAcademica) -> List[SchedulingAssignment]:
        """Genera asignaciones usando algoritmo genético"""
        logger.info(f"Iniciando algoritmo genético: población={self.population_size}, generaciones={self.generations}")

        asignaciones = list(AsignacionDocente.objects.filter(
            planificacion=planificacion,
            is_activa=True
        ).select_related('docente', 'materia'))

        franjas = list(FranjaHoraria.objects.filter(is_activa=True))
        aulas = list(Aula.objects.filter(is_disponible=True))

        if not asignaciones or not franjas or not aulas:
            return []

        # Crear población inicial
        population = self._create_initial_population(asignaciones, franjas, aulas)

        # Evolucionar durante las generaciones especificadas
        for generation in range(self.generations):
            # Evaluar fitness de cada individuo
            fitness_scores = [self._evaluate_fitness(individual) for individual in population]

            # Seleccionar mejores individuos para reproducción
            selected = self._selection(population, fitness_scores)

            # Crear nueva generación
            new_population = []
            while len(new_population) < self.population_size:
                parent1, parent2 = random.sample(selected, 2)
                child = self._crossover(parent1, parent2)

                if random.random() < self.mutation_rate:
                    child = self._mutate(child, franjas, aulas)

                new_population.append(child)

            population = new_population

            if generation % 20 == 0:
                best_fitness = max(fitness_scores)
                logger.info(f"Generación {generation}: mejor fitness = {best_fitness:.2f}")

        # Retornar el mejor individuo
        final_fitness = [self._evaluate_fitness(individual) for individual in population]
        best_individual = population[final_fitness.index(max(final_fitness))]

        logger.info(f"Algoritmo genético completado. Fitness final: {max(final_fitness):.2f}")
        return best_individual

    def _create_initial_population(self, asignaciones: List, franjas: List, aulas: List) -> List[List[SchedulingAssignment]]:
        """Crea población inicial aleatoria"""
        population = []

        for _ in range(self.population_size):
            individual = []
            used_resources = set()

            for asignacion in asignaciones:
                # Intentar asignar horario para esta materia
                attempts = 0
                while attempts < 50:  # Máximo 50 intentos por asignación
                    franja = random.choice(franjas)
                    aula = random.choice(aulas)

                    resource_key = (asignacion.docente.id, franja.id, aula.id)
                    docente_franja = (asignacion.docente.id, franja.id)
                    aula_franja = (aula.id, franja.id)

                    if docente_franja not in used_resources and aula_franja not in used_resources:
                        capacidad = min(30, int(aula.capacidad * 0.8))

                        assignment = SchedulingAssignment(
                            asignacion_docente=asignacion,
                            franja_horaria=franja,
                            aula=aula,
                            capacidad_estudiantes=capacidad,
                            modalidad='presencial'
                        )

                        individual.append(assignment)
                        used_resources.add(docente_franja)
                        used_resources.add(aula_franja)
                        break

                    attempts += 1

            population.append(individual)

        return population

    def _evaluate_fitness(self, individual: List[SchedulingAssignment]) -> float:
        """Evalúa el fitness de un individuo"""
        fitness = 0.0

        for assignment in individual:
            # Validar restricciones duras
            is_valid, violations = self.validate_assignment(assignment)
            if not is_valid:
                fitness -= 100  # Penalización severa por violaciones
            else:
                fitness += 50   # Bonificación por asignación válida

            # Agregar score de la asignación individual
            fitness += self.calculate_assignment_score(assignment)

        # Bonificación por completitud (cuántas asignaciones se lograron)
        completeness_bonus = len(individual) * 10
        fitness += completeness_bonus

        return fitness

    def _selection(self, population: List, fitness_scores: List[float]) -> List:
        """Selección por torneo para reproducción"""
        selected = []
        tournament_size = 3

        for _ in range(len(population) // 2):
            # Selección por torneo
            tournament_indices = random.sample(range(len(population)), tournament_size)
            winner_index = max(tournament_indices, key=lambda i: fitness_scores[i])
            selected.append(population[winner_index])

        return selected

    def _crossover(self, parent1: List, parent2: List) -> List:
        """Cruzamiento de dos individuos"""
        if not parent1 or not parent2:
            return parent1 if parent1 else parent2

        # Crossover de un punto
        crossover_point = random.randint(1, min(len(parent1), len(parent2)) - 1)

        child = parent1[:crossover_point] + parent2[crossover_point:]

        # Eliminar asignaciones duplicadas (mismo docente en misma franja)
        seen_docente_franja = set()
        seen_aula_franja = set()
        valid_child = []

        for assignment in child:
            docente_franja = (assignment.asignacion_docente.docente.id, assignment.franja_horaria.id)
            aula_franja = (assignment.aula.id, assignment.franja_horaria.id)

            if docente_franja not in seen_docente_franja and aula_franja not in seen_aula_franja:
                valid_child.append(assignment)
                seen_docente_franja.add(docente_franja)
                seen_aula_franja.add(aula_franja)

        return valid_child

    def _mutate(self, individual: List, franjas: List, aulas: List) -> List:
        """Mutación de un individuo"""
        if not individual:
            return individual

        # Mutar una asignación aleatoria
        mutation_index = random.randint(0, len(individual) - 1)
        assignment = individual[mutation_index]

        # Cambiar franja o aula aleatoriamente
        if random.random() < 0.5:
            # Cambiar franja horaria
            new_franja = random.choice(franjas)
            individual[mutation_index] = SchedulingAssignment(
                asignacion_docente=assignment.asignacion_docente,
                franja_horaria=new_franja,
                aula=assignment.aula,
                capacidad_estudiantes=assignment.capacidad_estudiantes,
                modalidad=assignment.modalidad
            )
        else:
            # Cambiar aula
            new_aula = random.choice(aulas)
            capacidad = min(30, int(new_aula.capacidad * 0.8))
            individual[mutation_index] = SchedulingAssignment(
                asignacion_docente=assignment.asignacion_docente,
                franja_horaria=assignment.franja_horaria,
                aula=new_aula,
                capacidad_estudiantes=capacidad,
                modalidad=assignment.modalidad
            )

        return individual


# Factory para crear motores de planificación
class SchedulingEngineFactory:
    """Factory para crear diferentes tipos de motores de planificación"""

    @staticmethod
    def create_engine(strategy: SchedulingStrategy, **kwargs) -> BaseSchedulingEngine:
        """Crea un motor de planificación según la estrategia especificada"""

        if strategy == SchedulingStrategy.DOCENTE_PRIORITY:
            return DocentePriorityEngine()

        elif strategy == SchedulingStrategy.AULA_OPTIMIZATION:
            return AulaOptimizationEngine()

        elif strategy == SchedulingStrategy.BALANCED_DISTRIBUTION:
            return BalancedDistributionEngine()

        elif strategy == SchedulingStrategy.GENETIC_ALGORITHM:
            population_size = kwargs.get('population_size', 50)
            generations = kwargs.get('generations', 100)
            return GeneticAlgorithmEngine(population_size, generations)

        else:
            raise ValueError(f"Estrategia no soportada: {strategy}")

    @staticmethod
    def get_available_strategies() -> List[Dict]:
        """Retorna lista de estrategias disponibles con descripciones"""
        return [
            {
                'key': SchedulingStrategy.DOCENTE_PRIORITY.value,
                'name': 'Prioridad Docente',
                'description': 'Optimiza horarios basándose en preferencias y disponibilidad de docentes'
            },
            {
                'key': SchedulingStrategy.AULA_OPTIMIZATION.value,
                'name': 'Optimización de Aulas',
                'description': 'Maximiza la eficiencia en el uso de aulas disponibles'
            },
            {
                'key': SchedulingStrategy.BALANCED_DISTRIBUTION.value,
                'name': 'Distribución Equilibrada',
                'description': 'Balancea la carga horaria uniformemente durante la semana'
            },
            {
                'key': SchedulingStrategy.GENETIC_ALGORITHM.value,
                'name': 'Algoritmo Genético',
                'description': 'Optimización avanzada usando algoritmos evolutivos'
            }
        ]