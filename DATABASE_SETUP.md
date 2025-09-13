# Configuración de Base de Datos

## Estado Actual

✅ **PostgreSQL Configurado con Docker**
- Container: `horarios_postgres` ejecutándose en puerto 5432
- Base de datos: `horarios_db` creada correctamente
- Usuario: `postgres` / Password: `postgres`

❌ **Problema de Encoding en Windows**
- Error: `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xf3`
- Causa: Conflicto entre encoding del sistema Windows y PostgreSQL
- Estado: Container funcionando, pero Django no puede conectar desde Windows

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

## Para Producción

1. Usar `settings_postgresql.py` o `settings.py`
2. Configurar variables de entorno correctamente
3. El container PostgreSQL está listo para recibir conexiones