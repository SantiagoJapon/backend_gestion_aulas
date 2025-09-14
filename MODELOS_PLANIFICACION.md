# Sistema de Planificación Académica - Modelos Implementados

## ✅ Estado Actual: COMPLETADO

Se ha implementado un sistema completo de planificación académica con todos los modelos necesarios para la gestión de horarios universitarios.

## 📋 Modelos Implementados

### **app: planificacion**

#### **1. Carrera**
- Gestión de programas académicos
- Campos: código, nombre, descripción, duración en semestres
- Relaciones: One-to-Many con Materias

#### **2. Periodo**
- Gestión de períodos académicos (semestres, cuatrimestres, etc.)
- Campos: nombre, tipo, año, fechas de inicio/fin
- Validaciones: fechas coherentes, períodos únicos

#### **3. Materia**
- Gestión de asignaturas
- Campos: código, nombre, créditos, horas semanales, semestre
- Relaciones: ForeignKey a Carrera, ManyToMany consigo misma (prerrequisitos)

#### **4. FranjaHoraria**
- Definición de bloques de tiempo
- Campos: día de la semana, hora inicio/fin, duración automática
- Validaciones: horarios coherentes, sin solapamientos

#### **5. PlanificacionAcademica**
- Contenedor principal de planificaciones
- Estados: borrador → revisión → aprobada → vigente → cerrada
- Métodos: activar(), get_total_materias(), get_total_horas_semanales()

### **app: asignaciones**

#### **6. AsignacionDocente**
- Asignación de docentes a materias
- Campos: docente, materia, planificación, carga horaria
- Restricciones: un docente por materia por planificación

#### **7. HorarioClase**
- Horarios específicos de clases
- Campos: asignación, franja horaria, aula, capacidad, modalidad
- Validaciones:
  - Capacidad no excede aula
  - Docente sin conflictos de horario
  - Aula disponible en la franja

#### **8. RegistroAsistencia**
- Control de asistencia estudiantil
- Campos: estudiante, fecha, presente, tarde, justificada
- Métodos: seguimiento de asistencia por períodos

#### **9. ConflictoHorario**
- Detección y gestión de conflictos
- Tipos: sobrecarga docente, aula ocupada, conflictos estudiantes
- Método: detectar_conflictos_planificacion() (automático)

## 🔧 Funcionalidades Implementadas

### **Validaciones Automáticas**
- ✅ Coherencia de fechas y horarios
- ✅ Capacidad de aulas vs estudiantes
- ✅ Conflictos de horario para docentes
- ✅ Disponibilidad de aulas por franja

### **Detección de Conflictos**
- ✅ Docentes con sobrecarga horaria (>40h/semana)
- ✅ Aulas ocupadas múltiples veces
- ✅ Conflictos de prerrequisitos
- ✅ Capacidades excedidas

### **Métodos de Utilidad**
- ✅ Cálculo de porcentajes de asistencia
- ✅ Estadísticas de planificación
- ✅ Gestión de estados de planificación
- ✅ Estudiantes inscritos por clase

## 📊 Datos de Prueba Creados

### **Usuarios (9 total)**
- 1 Administrador: `admin/admin123`
- 1 Director: `director/director123`
- 4 Docentes: `docente1/docente123`, `docente2/docente123`, etc.
- 3 Estudiantes: `estudiante1/estudiante123`, etc.

### **Estructura Académica**
- **3 Carreras**: Ingeniería en Software, Ingeniería Electrónica, Ingeniería en Gestión
- **6 Materias**: Matemáticas I, Física I, Programación I/II, Base de Datos I, Ing. Software
- **12 Franjas Horarias**: Lunes a Viernes, 3 bloques por día
- **1 Período**: 2do Semestre 2024 (Sep 2024 - Ene 2025)

### **Planificación**
- **1 Planificación Académica** activa y vigente
- **4 Asignaciones de Docentes** a materias específicas
- **Sistema listo** para crear horarios de clase

## 🚀 Próximos Pasos Sugeridos

1. **Crear APIs REST** para los nuevos modelos
2. **Desarrollar vistas de administración** Django Admin
3. **Implementar algoritmo de asignación automática** de horarios
4. **Crear reportes** de planificación y conflictos
5. **Integrar con frontend** React/Vue para gestión visual

## 🛠️ Uso del Sistema

### **Activar entorno y probar**
```bash
# Iniciar servidor
python manage.py runserver --settings=horarios_backend.settings_dev

# Acceder al admin
http://localhost:8000/admin/
# Usuario: admin / Contraseña: admin123
```

### **Estructura de la BD**
- ✅ **SQLite**: Desarrollo local funcionando
- ✅ **PostgreSQL**: Configurado para producción
- ✅ **Migraciones**: Aplicadas correctamente
- ✅ **Datos de prueba**: Cargados y verificados

## 📋 Resumen Técnico

**Modelos**: 9 modelos completos con relaciones
**Validaciones**: 15+ validaciones implementadas
**Métodos**: 10+ métodos de utilidad
**Estados**: Workflow completo de planificación
**Datos**: Sistema funcional con datos reales de prueba

El sistema está **100% funcional** y listo para integración con APIs y frontend.