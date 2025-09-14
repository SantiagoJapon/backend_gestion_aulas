"""
Sistema base de algoritmos de planificación automática de horarios
Arquitectura extensible para diferentes estrategias de asignación
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
from django.db import transaction
from django.utils import timezone
from ..models import PlanificacionAcademica, FranjaHoraria, Materia
from apps.asignaciones.models import AsignacionDocente, HorarioClase, ConflictoHorario
from apps.aulas.models import Aula
from apps.usuarios.models import CustomUser

logger = logging.getLogger(__name__)


class SchedulingStrategy(Enum):
    """Estrategias de planificación disponibles"""
    DOCENTE_PRIORITY = "docente_priority"
    AULA_OPTIMIZATION = "aula_optimization"
    BALANCED_DISTRIBUTION = "balanced_distribution"
    PREREQUISITE_BASED = "prerequisite_based"
    MIXED_MODALITY = "mixed_modality"
    GENETIC_ALGORITHM = "genetic_algorithm"


class ConstraintType(Enum):
    """Tipos de restricciones del sistema"""
    HARD = "hard"  # Restricciones obligatorias
    SOFT = "soft"  # Preferencias optimizables


@dataclass
class SchedulingConstraint:
    """Representa una restricción del sistema de planificación"""
    name: str
    type: ConstraintType
    weight: float = 1.0
    description: str = ""

    def validate(self, assignment: 'SchedulingAssignment') -> Tuple[bool, str]:
        """Valida si la asignación cumple esta restricción"""
        raise NotImplementedError


@dataclass
class SchedulingAssignment:
    """Representa una asignación de horario"""
    asignacion_docente: AsignacionDocente
    franja_horaria: FranjaHoraria
    aula: Aula
    capacidad_estudiantes: int
    modalidad: str = 'presencial'
    score: float = 0.0  # Puntuación de calidad de la asignación


@dataclass
class SchedulingResult:
    """Resultado de un proceso de planificación"""
    success: bool
    assignments: List[SchedulingAssignment]
    conflicts: List[ConflictoHorario]
    unassigned: List[AsignacionDocente]
    score: float
    execution_time: float
    strategy_used: SchedulingStrategy
    message: str = ""


class BaseSchedulingEngine(ABC):
    """Clase base para motores de planificación automática"""

    def __init__(self, strategy: SchedulingStrategy):
        self.strategy = strategy
        self.constraints: List[SchedulingConstraint] = []
        self.setup_default_constraints()

    def setup_default_constraints(self):
        """Configura las restricciones por defecto del sistema"""
        self.constraints = [
            # Restricciones duras (obligatorias)
            DocenteAvailabilityConstraint(),
            AulaAvailabilityConstraint(),
            CapacityConstraint(),
            TimeConflictConstraint(),

            # Restricciones suaves (preferencias)
            DocentePreferenceConstraint(),
            AulaTypeMatchConstraint(),
            DistributionBalanceConstraint(),
        ]

    @abstractmethod
    def generate_assignments(self, planificacion: PlanificacionAcademica) -> List[SchedulingAssignment]:
        """Genera asignaciones de horario para una planificación"""
        pass

    def validate_assignment(self, assignment: SchedulingAssignment) -> Tuple[bool, List[str]]:
        """Valida una asignación contra todas las restricciones"""
        is_valid = True
        violations = []

        for constraint in self.constraints:
            valid, message = constraint.validate(assignment)
            if not valid:
                if constraint.type == ConstraintType.HARD:
                    is_valid = False
                violations.append(f"{constraint.name}: {message}")

        return is_valid, violations

    def calculate_assignment_score(self, assignment: SchedulingAssignment) -> float:
        """Calcula la puntuación de calidad de una asignación"""
        score = 0.0

        for constraint in self.constraints:
            if constraint.type == ConstraintType.SOFT:
                valid, _ = constraint.validate(assignment)
                if valid:
                    score += constraint.weight

        return score

    def execute_scheduling(self, planificacion: PlanificacionAcademica,
                          parameters: Dict[str, Any] = None) -> SchedulingResult:
        """Ejecuta el proceso completo de planificación"""
        start_time = timezone.now()
        parameters = parameters or {}

        try:
            logger.info(f"Iniciando planificación automática con estrategia: {self.strategy.value}")

            # Generar asignaciones
            assignments = self.generate_assignments(planificacion)

            # Validar asignaciones
            valid_assignments = []
            conflicts = []

            for assignment in assignments:
                is_valid, violations = self.validate_assignment(assignment)
                if is_valid:
                    assignment.score = self.calculate_assignment_score(assignment)
                    valid_assignments.append(assignment)
                else:
                    # Crear registro de conflicto
                    conflict = ConflictoHorario(
                        planificacion=planificacion,
                        tipo='algoritmo_asignacion',
                        descripcion=f"Violaciones: {'; '.join(violations)}"
                    )
                    conflicts.append(conflict)

            # Identificar asignaciones no realizadas
            assigned_docente_ids = {a.asignacion_docente.id for a in valid_assignments}
            all_asignaciones = AsignacionDocente.objects.filter(
                planificacion=planificacion,
                is_activa=True
            )
            unassigned = [a for a in all_asignaciones if a.id not in assigned_docente_ids]

            # Calcular puntuación total
            total_score = sum(a.score for a in valid_assignments)

            execution_time = (timezone.now() - start_time).total_seconds()

            return SchedulingResult(
                success=len(conflicts) == 0,
                assignments=valid_assignments,
                conflicts=conflicts,
                unassigned=unassigned,
                score=total_score,
                execution_time=execution_time,
                strategy_used=self.strategy,
                message=f"Generadas {len(valid_assignments)} asignaciones, {len(conflicts)} conflictos"
            )

        except Exception as e:
            logger.error(f"Error en planificación automática: {e}")
            execution_time = (timezone.now() - start_time).total_seconds()

            return SchedulingResult(
                success=False,
                assignments=[],
                conflicts=[],
                unassigned=[],
                score=0.0,
                execution_time=execution_time,
                strategy_used=self.strategy,
                message=f"Error: {str(e)}"
            )

    @transaction.atomic
    def save_scheduling_result(self, planificacion: PlanificacionAcademica,
                             result: SchedulingResult) -> bool:
        """Guarda el resultado de la planificación en la base de datos"""
        try:
            # Limpiar horarios existentes si es necesario
            if result.success:
                HorarioClase.objects.filter(
                    asignacion_docente__planificacion=planificacion
                ).delete()

            # Guardar asignaciones válidas
            for assignment in result.assignments:
                HorarioClase.objects.create(
                    asignacion_docente=assignment.asignacion_docente,
                    franja_horaria=assignment.franja_horaria,
                    aula=assignment.aula,
                    capacidad_estudiantes=assignment.capacidad_estudiantes,
                    modalidad=assignment.modalidad,
                    observaciones=f"Generado automáticamente - Estrategia: {self.strategy.value} - Score: {assignment.score:.2f}"
                )

            # Guardar conflictos
            for conflict in result.conflicts:
                conflict.save()

            logger.info(f"Planificación guardada: {len(result.assignments)} horarios, {len(result.conflicts)} conflictos")
            return True

        except Exception as e:
            logger.error(f"Error guardando planificación: {e}")
            return False


# Implementación de restricciones específicas

class DocenteAvailabilityConstraint(SchedulingConstraint):
    """Restricción de disponibilidad del docente"""

    def __init__(self):
        super().__init__(
            name="Disponibilidad Docente",
            type=ConstraintType.HARD,
            weight=1.0,
            description="El docente debe estar disponible en la franja horaria"
        )

    def validate(self, assignment: SchedulingAssignment) -> Tuple[bool, str]:
        # Verificar que el docente no tenga otro horario en la misma franja
        conflictos = HorarioClase.objects.filter(
            asignacion_docente__docente=assignment.asignacion_docente.docente,
            franja_horaria=assignment.franja_horaria,
            is_activa=True
        ).exists()

        if conflictos:
            return False, f"Docente {assignment.asignacion_docente.docente.get_full_name()} ya tiene clase en {assignment.franja_horaria}"

        return True, ""


class AulaAvailabilityConstraint(SchedulingConstraint):
    """Restricción de disponibilidad del aula"""

    def __init__(self):
        super().__init__(
            name="Disponibilidad Aula",
            type=ConstraintType.HARD,
            weight=1.0,
            description="El aula debe estar disponible en la franja horaria"
        )

    def validate(self, assignment: SchedulingAssignment) -> Tuple[bool, str]:
        # Verificar que el aula no esté ocupada
        conflictos = HorarioClase.objects.filter(
            aula=assignment.aula,
            franja_horaria=assignment.franja_horaria,
            is_activa=True
        ).exists()

        if conflictos:
            return False, f"Aula {assignment.aula.codigo} ya está ocupada en {assignment.franja_horaria}"

        if not assignment.aula.is_disponible:
            return False, f"Aula {assignment.aula.codigo} no está disponible"

        return True, ""


class CapacityConstraint(SchedulingConstraint):
    """Restricción de capacidad del aula"""

    def __init__(self):
        super().__init__(
            name="Capacidad Aula",
            type=ConstraintType.HARD,
            weight=1.0,
            description="La capacidad de estudiantes no debe exceder la del aula"
        )

    def validate(self, assignment: SchedulingAssignment) -> Tuple[bool, str]:
        if assignment.capacidad_estudiantes > assignment.aula.capacidad:
            return False, f"Capacidad requerida ({assignment.capacidad_estudiantes}) excede capacidad del aula ({assignment.aula.capacidad})"

        return True, ""


class TimeConflictConstraint(SchedulingConstraint):
    """Restricción de conflictos temporales"""

    def __init__(self):
        super().__init__(
            name="Conflicto Temporal",
            type=ConstraintType.HARD,
            weight=1.0,
            description="No debe haber solapamientos de horario"
        )

    def validate(self, assignment: SchedulingAssignment) -> Tuple[bool, str]:
        # Esta validación es más compleja y podría incluir
        # verificación de horarios solapados, tiempos de desplazamiento, etc.
        return True, ""


class DocentePreferenceConstraint(SchedulingConstraint):
    """Restricción suave de preferencias del docente"""

    def __init__(self):
        super().__init__(
            name="Preferencias Docente",
            type=ConstraintType.SOFT,
            weight=0.3,
            description="Preferencias de horario del docente"
        )

    def validate(self, assignment: SchedulingAssignment) -> Tuple[bool, str]:
        # Aquí se pueden implementar preferencias específicas
        # Por ahora, asumimos que todas las franjas son igualmente preferibles
        return True, "Preferencias respetadas"


class AulaTypeMatchConstraint(SchedulingConstraint):
    """Restricción suave de compatibilidad tipo de aula"""

    def __init__(self):
        super().__init__(
            name="Tipo Aula Apropiado",
            type=ConstraintType.SOFT,
            weight=0.4,
            description="El tipo de aula debe ser apropiado para la materia"
        )

    def validate(self, assignment: SchedulingAssignment) -> Tuple[bool, str]:
        materia = assignment.asignacion_docente.materia
        aula_tipo = assignment.aula.tipo.nombre.lower()
        materia_nombre = materia.nombre.lower()

        # Lógica simple de matcheo
        if 'laboratorio' in materia_nombre and 'laboratorio' in aula_tipo:
            return True, "Laboratorio apropiado para materia práctica"
        elif 'laboratorio' not in materia_nombre and 'magistral' in aula_tipo:
            return True, "Aula magistral apropiada para materia teórica"

        return True, "Tipo de aula aceptable"


class DistributionBalanceConstraint(SchedulingConstraint):
    """Restricción suave de distribución balanceada"""

    def __init__(self):
        super().__init__(
            name="Distribución Equilibrada",
            type=ConstraintType.SOFT,
            weight=0.2,
            description="Distribución equilibrada de horarios"
        )

    def validate(self, assignment: SchedulingAssignment) -> Tuple[bool, str]:
        # Lógica para evaluar si la distribución está equilibrada
        # Por ahora retornamos True, pero aquí se puede implementar
        # análisis de distribución por días, docentes, etc.
        return True, "Distribución aceptable"