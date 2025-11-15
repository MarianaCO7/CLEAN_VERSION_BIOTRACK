-- ============================================================================
-- 🗄️ SCHEMA DE BASE DE DATOS - SISTEMA DE ANÁLISIS BIOMECÁNICO EDUCATIVO
-- ============================================================================
-- Versión: 9.5 - Educational Edition
-- Fecha: 2025-11-14
-- Descripción: Estructura completa de la base de datos SQLite (Enfoque Educativo)
-- Roles: Administradores y Estudiantes
-- ============================================================================

-- Eliminar tablas existentes (en orden inverso por dependencias)
DROP TABLE IF EXISTS angle_measurement;
DROP TABLE IF EXISTS system_log;
DROP TABLE IF EXISTS rom_session;
DROP TABLE IF EXISTS subject;
DROP TABLE IF EXISTS user;

-- ============================================================================
-- TABLA: user (Usuarios del Sistema - Administradores y Estudiantes)
-- ============================================================================
CREATE TABLE user (
    -- Identificación
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    -- Información Personal
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    
    -- Información Académica
    role VARCHAR(20) NOT NULL DEFAULT 'student',
        -- Valores: 'admin', 'student'
    student_id VARCHAR(50),
        -- Código de matrícula del estudiante (ej: EST-2024-0123)
    program VARCHAR(100),
        -- Programa académico (ej: 'Ingeniería Biomédica', 'Fisioterapia', 'Kinesiología')
    semester INTEGER,
        -- Semestre actual del estudiante (1-10)
    
    -- Datos Antropométricos (para Drillis & Contini)
    height FLOAT,
        -- Altura del usuario en centímetros (necesaria para aproximación de Drillis & Contini)
        -- Usada para calcular longitudes de segmentos corporales
    
    -- Estado y Auditoría
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_by INTEGER,
        -- ID del administrador que creó este usuario (NULL para el primer admin)
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    
    -- Relaciones
    FOREIGN KEY (created_by) REFERENCES user(id) ON DELETE SET NULL,
    
    -- Validaciones
    CHECK (role IN ('admin', 'student')),
    CHECK (is_active IN (0, 1)),
    CHECK (semester IS NULL OR (semester >= 1 AND semester <= 12)),
    CHECK (height IS NULL OR (height >= 50 AND height <= 250))
        -- Altura válida entre 50cm y 250cm
);

-- Índices para optimización
CREATE INDEX idx_user_username ON user(username);
CREATE INDEX idx_user_email ON user(email);
CREATE INDEX idx_user_role ON user(role);
CREATE INDEX idx_user_student_id ON user(student_id);
CREATE INDEX idx_user_created_by ON user(created_by);
CREATE INDEX idx_user_is_active ON user(is_active);

-- ============================================================================
-- TABLA: subject (Sujetos de Estudio - Contexto Educativo)
-- ============================================================================
CREATE TABLE subject (
    -- Identificación
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_code VARCHAR(50) UNIQUE NOT NULL,
        -- Código único generado automáticamente: SUJ-YYYY-NNNN
    
    -- Información Personal
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE,
    gender VARCHAR(10),
        -- Valores: 'M', 'F', 'Other'
    
    -- Información Física
    height FLOAT,
        -- Altura en centímetros
    
    -- Información Adicional (Contexto Educativo)
    activity_level VARCHAR(50),
        -- Nivel de actividad física: 'sedentary', 'light', 'moderate', 'active', 'very_active'
    notes TEXT,
        -- Observaciones y notas del estudio
    
    -- Auditoría
    created_by INTEGER NOT NULL,
        -- ID del estudiante que registró al sujeto
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Relaciones
    FOREIGN KEY (created_by) REFERENCES user(id) ON DELETE RESTRICT,
    
    -- Validaciones
    CHECK (gender IN ('M', 'F', 'Other') OR gender IS NULL),
    CHECK (height IS NULL OR (height >= 50 AND height <= 250)),
    CHECK (activity_level IN ('sedentary', 'light', 'moderate', 'active', 'very_active') OR activity_level IS NULL)
);

-- Índices para optimización
CREATE INDEX idx_subject_code ON subject(subject_code);
CREATE INDEX idx_subject_created_by ON subject(created_by);
CREATE INDEX idx_subject_last_name ON subject(last_name);

-- ============================================================================
-- TABLA: rom_session (Sesiones de Análisis de Rango de Movimiento)
-- ============================================================================
CREATE TABLE rom_session (
    -- Identificación
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Relaciones
    subject_id INTEGER NOT NULL,
        -- Sujeto analizado
    user_id INTEGER NOT NULL,
        -- Estudiante que realizó el análisis
    
    -- Configuración del Análisis
    segment VARCHAR(50) NOT NULL,
        -- Segmento corporal: 'ankle', 'knee', 'hip', 'shoulder', 'elbow'
    exercise_type VARCHAR(50) NOT NULL,
        -- Tipo de movimiento: 'flexion', 'extension', 'abduction', 'adduction', 
        -- 'internal_rotation', 'external_rotation', 'dorsiflexion', 'plantarflexion'
    camera_view VARCHAR(20),
        -- Vista de cámara: 'lateral', 'frontal', 'posterior'
    side VARCHAR(20),
        -- Lado analizado: 'left', 'right', 'bilateral'
    
    -- Resultados del Análisis
    max_angle FLOAT,
        -- Ángulo máximo alcanzado (grados)
    min_angle FLOAT,
        -- Ángulo mínimo alcanzado (grados)
    rom_value FLOAT,
        -- Rango de movimiento total (max - min)
    repetitions INTEGER DEFAULT 0,
        -- Número de repeticiones detectadas
    duration FLOAT,
        -- Duración del análisis en segundos
    quality_score FLOAT,
        -- Puntuación de calidad del análisis (0-100)
    
    -- Información Adicional
    notes TEXT,
        -- Observaciones del estudiante
    video_path VARCHAR(500),
        -- Ruta al video grabado (si existe)
    
    -- Auditoría
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Relaciones
    FOREIGN KEY (subject_id) REFERENCES subject(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE RESTRICT,
    
    -- Validaciones
    CHECK (segment IN ('ankle', 'knee', 'hip', 'shoulder', 'elbow')),
    CHECK (camera_view IN ('lateral', 'frontal', 'posterior') OR camera_view IS NULL),
    CHECK (side IN ('left', 'right', 'bilateral') OR side IS NULL),
    CHECK (max_angle IS NULL OR (max_angle >= 0 AND max_angle <= 360)),
    CHECK (min_angle IS NULL OR (min_angle >= 0 AND min_angle <= 360)),
    CHECK (rom_value IS NULL OR (rom_value >= 0 AND rom_value <= 360)),
    CHECK (quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100))
);

-- Índices para optimización
CREATE INDEX idx_rom_session_subject ON rom_session(subject_id);
CREATE INDEX idx_rom_session_user ON rom_session(user_id);
CREATE INDEX idx_rom_session_segment ON rom_session(segment);
CREATE INDEX idx_rom_session_exercise ON rom_session(exercise_type);
CREATE INDEX idx_rom_session_date ON rom_session(created_at);

-- ============================================================================
-- TABLA: angle_measurement (Mediciones de Ángulos Frame-by-Frame)
-- ============================================================================
CREATE TABLE angle_measurement (
    -- Identificación
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
        -- Sesión a la que pertenece esta medición
    
    -- Datos de la Medición
    timestamp FLOAT NOT NULL,
        -- Timestamp relativo en segundos desde el inicio
    frame_number INTEGER NOT NULL,
        -- Número de frame del video
    angle_value FLOAT NOT NULL,
        -- Ángulo medido en grados
    confidence FLOAT,
        -- Confianza de MediaPipe (0-1)
    landmarks_json TEXT,
        -- JSON con coordenadas de landmarks (opcional, para debugging)
    
    -- Relaciones
    FOREIGN KEY (session_id) REFERENCES rom_session(id) ON DELETE CASCADE,
    
    -- Validaciones
    CHECK (angle_value >= 0 AND angle_value <= 360),
    CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
);

-- Índices para optimización
CREATE INDEX idx_angle_measurement_session ON angle_measurement(session_id);
CREATE INDEX idx_angle_measurement_frame ON angle_measurement(frame_number);

-- ============================================================================
-- TABLA: system_log (Registro de Actividad del Sistema)
-- ============================================================================
CREATE TABLE system_log (
    -- Identificación
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Información del Evento
    user_id INTEGER,
        -- Usuario que realizó la acción (NULL para eventos del sistema)
    action VARCHAR(100) NOT NULL,
        -- Tipo de acción: 'login', 'logout', 'create_subject', 'start_analysis',
        -- 'export_report', 'delete_session', etc.
    details TEXT,
        -- Detalles adicionales en formato JSON o texto
    ip_address VARCHAR(45),
        -- Dirección IP del cliente
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Relaciones
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE SET NULL
);

-- Índices para optimización
CREATE INDEX idx_system_log_user ON system_log(user_id);
CREATE INDEX idx_system_log_action ON system_log(action);
CREATE INDEX idx_system_log_timestamp ON system_log(timestamp);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger para actualizar automáticamente updated_at en subject
CREATE TRIGGER update_subject_timestamp 
AFTER UPDATE ON subject
FOR EACH ROW
BEGIN
    UPDATE subject SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

-- ============================================================================
-- VISTAS (Views para consultas comunes)
-- ============================================================================

-- Vista: Resumen de sujetos con estadísticas de sesiones
CREATE VIEW v_subject_summary AS
SELECT 
    s.id,
    s.subject_code,
    s.first_name || ' ' || s.last_name AS full_name,
    s.date_of_birth,
    s.gender,
    s.height,
    s.activity_level,
    COUNT(DISTINCT rs.id) AS total_sessions,
    MAX(rs.created_at) AS last_session_date,
    u.full_name AS created_by_name,
    u.student_id,
    u.program,
    s.created_at,
    s.updated_at
FROM subject s
LEFT JOIN rom_session rs ON s.id = rs.subject_id
LEFT JOIN user u ON s.created_by = u.id
GROUP BY s.id;

-- Vista: Resumen de sesiones con información del sujeto y estudiante
CREATE VIEW v_session_summary AS
SELECT 
    rs.id AS session_id,
    rs.segment,
    rs.exercise_type,
    rs.camera_view,
    rs.side,
    rs.max_angle,
    rs.min_angle,
    rs.rom_value,
    rs.repetitions,
    rs.duration,
    rs.quality_score,
    rs.created_at AS session_date,
    
    -- Información del Sujeto
    s.subject_code,
    s.first_name || ' ' || s.last_name AS subject_name,
    s.gender AS subject_gender,
    s.height AS subject_height,
    
    -- Información del Estudiante
    u.full_name AS student_name,
    u.student_id,
    u.program,
    u.semester,
    
    -- Estadísticas
    COUNT(am.id) AS total_measurements
FROM rom_session rs
JOIN subject s ON rs.subject_id = s.id
JOIN user u ON rs.user_id = u.id
LEFT JOIN angle_measurement am ON rs.id = am.session_id
GROUP BY rs.id;

-- Vista: Estadísticas por segmento corporal
CREATE VIEW v_segment_statistics AS
SELECT 
    segment,
    exercise_type,
    COUNT(*) AS total_sessions,
    AVG(rom_value) AS avg_rom,
    MIN(rom_value) AS min_rom,
    MAX(rom_value) AS max_rom,
    AVG(quality_score) AS avg_quality,
    AVG(duration) AS avg_duration
FROM rom_session
WHERE rom_value IS NOT NULL
GROUP BY segment, exercise_type
ORDER BY segment, exercise_type;

-- Vista: Actividad de estudiantes
CREATE VIEW v_student_activity AS
SELECT 
    u.id AS user_id,
    u.full_name,
    u.student_id,
    u.program,
    u.semester,
    COUNT(DISTINCT s.id) AS subjects_registered,
    COUNT(DISTINCT rs.id) AS sessions_performed,
    AVG(rs.quality_score) AS avg_quality,
    MAX(rs.created_at) AS last_activity,
    u.created_at AS registration_date,
    u.last_login
FROM user u
LEFT JOIN subject s ON u.id = s.created_by
LEFT JOIN rom_session rs ON u.id = rs.user_id
WHERE u.role = 'student'
GROUP BY u.id
ORDER BY sessions_performed DESC;

-- ============================================================================
-- COMENTARIOS FINALES
-- ============================================================================

-- Este schema está optimizado para un sistema educativo de análisis biomecánico
-- 
-- CARACTERÍSTICAS:
-- - 2 roles únicos: admin y student
-- - Tabla 'subject' en lugar de 'patient' (enfoque no clínico)
-- - Campos académicos: student_id, program, semester
-- - Sin información médica/clínica (license_number, institution, specialization)
-- - Vistas educativas: actividad de estudiantes, estadísticas de aprendizaje
--
-- 🔒 RESTRICCIÓN DE SEGURIDAD:
-- - Solo el ADMINISTRADOR puede crear usuarios estudiantes
-- - Campo created_by en tabla user registra qué admin creó cada estudiante
-- - Primer admin tiene created_by = NULL (auto-creado)
-- - Ver IMPLEMENTACION_RESTRICCION_ADMIN.md para detalles de implementación
--
-- PRÓXIMOS PASOS:
-- 1. Ejecutar este schema: sqlite3 biomech_system.db < schema.sql
-- 2. Cargar datos iniciales: sqlite3 biomech_system.db < seeds.sql
-- 3. Configurar primer administrador
--
-- ============================================================================
