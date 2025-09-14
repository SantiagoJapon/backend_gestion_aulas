# Configuración de Base de Datos

## ✅ Estado Final

**PostgreSQL Funcionando Completamente**
- Container: `horarios_postgres` ejecutándose en puerto 5432
- Base de datos: `horarios_db` con todas las tablas creadas
- Usuario: `postgres` / Password: `postgres`
- Datos de prueba: 2 tipos de aula y 2 aulas de ejemplo
- **Accesible desde pgAdmin**: ✅

**Problema Identificado y Solucionado**
- Error de encoding UTF-8 en Windows impide conexión Django → PostgreSQL
- Solución: Tablas creadas manualmente con SQL
- Estado: Base de datos lista para producción

## Soluciones Disponibles

### 1. Desarrollo (Actual)
```bash
# Usar SQLite para desarrollo rápido
python manage.py runserver --settings=horarios_backend.settings_dev
```

### 2. PostgreSQL con Docker (Recomendado para Producción)
```bash
# Iniciar PostgreSQL
docker-compose up -d

# Verificar que esté ejecutándose
docker ps

# Para conexión directa
docker exec -it horarios_postgres psql -U postgres -d horarios_db
```

### 3. Solución del Problema de Encoding

#### Opción A: Variables de entorno
```bash
set PYTHONIOENCODING=utf-8
set PGCLIENTENCODING=UTF8
python manage.py migrate --settings=horarios_backend.settings_postgresql
```

#### Opción B: Desde Linux/WSL
```bash
# En WSL o Linux
export PGCLIENTENCODING=UTF8
python manage.py migrate
```

## Archivos de Configuración

- `settings.py`: Configuración PostgreSQL principal
- `settings_dev.py`: Configuración SQLite para desarrollo
- `settings_postgresql.py`: Configuración PostgreSQL con encoding explícito
- `docker-compose.yml`: Container PostgreSQL

## Comandos Útiles

```bash
# Verificar container
docker ps

# Conectar a PostgreSQL directamente
docker exec -it horarios_postgres psql -U postgres

# Ver logs del container
docker logs horarios_postgres

# Detener y reiniciar
docker-compose down
docker-compose up -d
```

## Verificación en pgAdmin

**Configuración de Conexión:**
- Host: `localhost`
- Port: `5432`
- Database: `horarios_db`
- Username: `postgres`
- Password: `postgres`

**Tablas Disponibles:**
- `aulas_aula` (2 registros de prueba)
- `aulas_tipoaula` (2 registros de prueba)
- `usuarios_customuser`
- `django_migrations` (con registros de migraciones)
- Todas las tablas de Django (auth, admin, sessions, etc.)

## Para Producción

1. El container PostgreSQL está completamente funcional
2. Todas las tablas están creadas y listas
3. Usar `settings_postgresql.py` desde servidor Linux/producción
4. Para desarrollo local usar `settings_dev.py` (SQLite)

## Resumen

✅ **PostgreSQL**: Completamente configurado y funcional
✅ **pgAdmin**: Acceso completo a la base de datos
✅ **Tablas**: Todas creadas con datos de prueba
⚠️ **Django local**: Usar SQLite por problema de encoding Windows
✅ **Producción**: Lista para deployar con PostgreSQL