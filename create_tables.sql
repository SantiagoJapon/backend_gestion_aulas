-- SQL para crear las tablas de Django manualmente
-- Ejecutar esto en PostgreSQL para evitar problemas de encoding

-- Tabla de migraciones de Django
CREATE TABLE IF NOT EXISTS django_migrations (
    id SERIAL PRIMARY KEY,
    app VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    applied TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de tipos de contenido de Django
CREATE TABLE IF NOT EXISTS django_content_type (
    id SERIAL PRIMARY KEY,
    app_label VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    UNIQUE(app_label, model)
);

-- Tabla de permisos de Django
CREATE TABLE IF NOT EXISTS auth_permission (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    content_type_id INTEGER REFERENCES django_content_type(id),
    codename VARCHAR(100) NOT NULL,
    UNIQUE(content_type_id, codename)
);

-- Tabla de grupos de Django
CREATE TABLE IF NOT EXISTS auth_group (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL
);

-- Tabla de permisos de grupos
CREATE TABLE IF NOT EXISTS auth_group_permissions (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES auth_group(id),
    permission_id INTEGER REFERENCES auth_permission(id),
    UNIQUE(group_id, permission_id)
);

-- Tabla de usuarios personalizada
CREATE TABLE IF NOT EXISTS usuarios_customuser (
    id SERIAL PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(150) UNIQUE NOT NULL,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    email VARCHAR(254) NOT NULL DEFAULT '',
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    rol VARCHAR(20) NOT NULL DEFAULT 'estudiante',
    cedula VARCHAR(10) UNIQUE,
    telegram_id VARCHAR(50)
);

-- Tabla de permisos de usuarios
CREATE TABLE IF NOT EXISTS usuarios_customuser_user_permissions (
    id SERIAL PRIMARY KEY,
    customuser_id INTEGER REFERENCES usuarios_customuser(id),
    permission_id INTEGER REFERENCES auth_permission(id),
    UNIQUE(customuser_id, permission_id)
);

-- Tabla de grupos de usuarios
CREATE TABLE IF NOT EXISTS usuarios_customuser_groups (
    id SERIAL PRIMARY KEY,
    customuser_id INTEGER REFERENCES usuarios_customuser(id),
    group_id INTEGER REFERENCES auth_group(id),
    UNIQUE(customuser_id, group_id)
);

-- Tabla de tipos de aula
CREATE TABLE IF NOT EXISTS aulas_tipoaula (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL,
    descripcion TEXT NOT NULL DEFAULT ''
);

-- Tabla de aulas
CREATE TABLE IF NOT EXISTS aulas_aula (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    capacidad INTEGER NOT NULL CHECK (capacidad >= 0),
    piso INTEGER NOT NULL CHECK (piso >= 0),
    edificio VARCHAR(50) NOT NULL,
    is_disponible BOOLEAN NOT NULL DEFAULT TRUE,
    tipo_id INTEGER REFERENCES aulas_tipoaula(id)
);

-- Tabla de sesiones de Django
CREATE TABLE IF NOT EXISTS django_session (
    session_key VARCHAR(40) PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS django_session_expire_date_idx ON django_session(expire_date);

-- Tabla de admin log
CREATE TABLE IF NOT EXISTS django_admin_log (
    id SERIAL PRIMARY KEY,
    action_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    object_id TEXT,
    object_repr VARCHAR(200) NOT NULL,
    action_flag SMALLINT NOT NULL CHECK (action_flag >= 0),
    change_message TEXT NOT NULL,
    content_type_id INTEGER REFERENCES django_content_type(id),
    user_id INTEGER REFERENCES usuarios_customuser(id)
);

-- Tabla de tokens de autenticación
CREATE TABLE IF NOT EXISTS authtoken_token (
    key VARCHAR(40) PRIMARY KEY,
    created TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER UNIQUE REFERENCES usuarios_customuser(id)
);

-- Insertar registros de migraciones
INSERT INTO django_migrations (app, name, applied) VALUES
('contenttypes', '0001_initial', CURRENT_TIMESTAMP),
('contenttypes', '0002_remove_content_type_name', CURRENT_TIMESTAMP),
('auth', '0001_initial', CURRENT_TIMESTAMP),
('auth', '0002_alter_permission_name_max_length', CURRENT_TIMESTAMP),
('auth', '0003_alter_user_email_max_length', CURRENT_TIMESTAMP),
('auth', '0004_alter_user_username_opts', CURRENT_TIMESTAMP),
('auth', '0005_alter_user_last_login_null', CURRENT_TIMESTAMP),
('auth', '0006_require_contenttypes_0002', CURRENT_TIMESTAMP),
('auth', '0007_alter_validators_add_error_messages', CURRENT_TIMESTAMP),
('auth', '0008_alter_user_username_max_length', CURRENT_TIMESTAMP),
('auth', '0009_alter_user_last_name_max_length', CURRENT_TIMESTAMP),
('auth', '0010_alter_group_name_max_length', CURRENT_TIMESTAMP),
('auth', '0011_update_proxy_permissions', CURRENT_TIMESTAMP),
('auth', '0012_alter_user_first_name_max_length', CURRENT_TIMESTAMP),
('usuarios', '0001_initial', CURRENT_TIMESTAMP),
('usuarios', '0002_alter_customuser_options_remove_customuser_carrera_and_more', CURRENT_TIMESTAMP),
('admin', '0001_initial', CURRENT_TIMESTAMP),
('admin', '0002_logentry_remove_auto_add', CURRENT_TIMESTAMP),
('admin', '0003_logentry_add_action_flag_choices', CURRENT_TIMESTAMP),
('authtoken', '0001_initial', CURRENT_TIMESTAMP),
('authtoken', '0002_auto_20160226_1747', CURRENT_TIMESTAMP),
('authtoken', '0003_tokenproxy', CURRENT_TIMESTAMP),
('authtoken', '0004_alter_tokenproxy_options', CURRENT_TIMESTAMP),
('sessions', '0001_initial', CURRENT_TIMESTAMP),
('aulas', '0001_initial', CURRENT_TIMESTAMP)
ON CONFLICT (app, name) DO NOTHING;