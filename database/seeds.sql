-- ============================================================================
-- 🌱 SEEDS - DATOS INICIALES PARA SISTEMA BIOMECÁNICO EDUCATIVO
-- ============================================================================
-- Versión: 9.5 - Educational Edition
-- Fecha: 2025-11-14
-- Descripción: Datos de ejemplo para desarrollo y testing (Enfoque Educativo)
-- ============================================================================

-- ============================================================================
-- USUARIOS DE PRUEBA (Administrador + Estudiantes)
-- ============================================================================

-- Nota: Los password_hash mostrados son solo ejemplos
-- En producción, usar: werkzeug.security.generate_password_hash('contraseña')
-- Contraseña de prueba para todos: 'test123'

INSERT INTO user (id, username, password_hash, full_name, email, role, student_id, program, semester, height, is_active, created_by) VALUES
-- 1. Administrador del Sistema (Auto-creado, no tiene created_by ni altura)
(1, 'admin', 
 'scrypt:32768:8:1$example$hashvalue1234567890abcdef',
 'Administrador del Sistema',
 'admin@universidad.edu.co',
 'admin',
 NULL,
 NULL,
 NULL,
 NULL,
 1,
 NULL),

-- 2. Estudiante de Ingeniería Biomédica (Semestre 8) - CREADO POR ADMIN
(2, 'carlos.mendez',
 'scrypt:32768:8:1$example$hashvalue1234567890abcdef',
 'Carlos Andrés Méndez Torres',
 'carlos.mendez@estudiantes.edu.co',
 'student',
 'EST-2021-0145',
 'Ingeniería Biomédica',
 8,
 175.0,
 1,
 1),

-- 3. Estudiante de Fisioterapia (Semestre 6) - CREADO POR ADMIN
(3, 'maria.rodriguez',
 'scrypt:32768:8:1$example$hashvalue1234567890abcdef',
 'María Fernanda Rodríguez López',
 'maria.rodriguez@estudiantes.edu.co',
 'student',
 'EST-2022-0089',
 'Fisioterapia',
 6,
 162.0,
 1,
 1),

-- 4. Estudiante de Kinesiología (Semestre 5) - CREADO POR ADMIN
(4, 'juan.garcia',
 'scrypt:32768:8:1$example$hashvalue1234567890abcdef',
 'Juan Pablo García Ramírez',
 'juan.garcia@estudiantes.edu.co',
 'student',
 'EST-2022-0234',
 'Kinesiología y Fisioterapia',
 5,
 180.0,
 1,
 1),

-- 5. Estudiante de Ingeniería Biomédica (Semestre 10 - Tesista) - CREADO POR ADMIN
(5, 'laura.martinez',
 'scrypt:32768:8:1$example$hashvalue1234567890abcdef',
 'Laura Camila Martínez Sánchez',
 'laura.martinez@estudiantes.edu.co',
 'student',
 'EST-2020-0056',
 'Ingeniería Biomédica',
 10,
 168.0,
 1,
 1);

-- ============================================================================
-- SUJETOS DE ESTUDIO (Participantes en prácticas académicas)
-- ============================================================================

INSERT INTO subject (id, subject_code, first_name, last_name, date_of_birth, gender, height, activity_level, notes, created_by) VALUES
-- Sujeto 1: Registrado por Carlos (estudiante de biomédica)
(1, 'SUJ-2024-0001',
 'Pedro',
 'González',
 '1998-05-15',
 'M',
 175.0,
 'moderate',
 'Sujeto voluntario para estudio de ROM de tobillo. Practica fútbol 2 veces por semana.',
 2),

-- Sujeto 2: Registrado por María (estudiante de fisioterapia)
(2, 'SUJ-2024-0002',
 'Ana',
 'Martínez',
 '2000-08-22',
 'F',
 162.0,
 'active',
 'Atleta amateur de atletismo. Participante en estudio de ROM de rodilla.',
 3),

-- Sujeto 3: Registrado por Juan (estudiante de kinesiología)
(3, 'SUJ-2024-0003',
 'Miguel',
 'Torres',
 '1997-12-10',
 'M',
 180.0,
 'light',
 'Oficinista. Participante en estudio de ROM de hombro y cadera.',
 4),

-- Sujeto 4: Registrado por Laura (tesista)
(4, 'SUJ-2024-0004',
 'Carolina',
 'Ramírez',
 '1999-03-18',
 'F',
 168.0,
 'very_active',
 'Bailarina profesional. Estudio completo de movilidad articular para tesis.',
 5),

-- Sujeto 5: Registrado por Carlos
(5, 'SUJ-2024-0005',
 'Roberto',
 'Silva',
 '2001-07-05',
 'M',
 172.0,
 'sedentary',
 'Sujeto sedentario. Estudio comparativo de ROM con sujeto activo.',
 2);

-- ============================================================================
-- SESIONES ROM (Análisis realizados por estudiantes)
-- ============================================================================

INSERT INTO rom_session (id, subject_id, user_id, segment, exercise_type, camera_view, side, max_angle, min_angle, rom_value, repetitions, duration, quality_score, notes) VALUES
-- Sesión 1: Carlos analiza tobillo de Pedro (dorsiflexión)
(1, 1, 2,
 'ankle',
 'dorsiflexion',
 'lateral',
 'left',
 110.5,
 85.2,
 25.3,
 5,
 45.2,
 92.5,
 'Práctica de laboratorio. ROM normal para dorsiflexión de tobillo.'),

-- Sesión 2: María analiza rodilla de Ana (flexión)
(2, 2, 3,
 'knee',
 'flexion',
 'lateral',
 'right',
 135.8,
 5.2,
 130.6,
 8,
 62.5,
 95.0,
 'Excelente ROM. Sujeto atleta muestra flexibilidad superior al promedio.'),

-- Sesión 3: Juan analiza hombro de Miguel (abducción)
(3, 3, 4,
 'shoulder',
 'abduction',
 'frontal',
 'right',
 168.5,
 12.3,
 156.2,
 6,
 58.0,
 88.5,
 'ROM ligeramente reducido. Posible limitación por sedentarismo.'),

-- Sesión 4: Laura analiza cadera de Carolina (flexión) - Tesis
(4, 4, 5,
 'hip',
 'flexion',
 'lateral',
 'left',
 125.5,
 8.5,
 117.0,
 10,
 75.5,
 97.0,
 'Datos para tesis de grado. ROM excepcional en bailarina profesional.'),

-- Sesión 5: Carlos analiza tobillo de Pedro (plantiflexión)
(5, 1, 2,
 'ankle',
 'plantarflexion',
 'lateral',
 'left',
 135.2,
 88.5,
 46.7,
 5,
 42.0,
 90.0,
 'Segunda medición en mismo sujeto. Plantiflexión dentro de valores normales.'),

-- Sesión 6: María analiza rodilla de Ana (extensión)
(6, 2, 3,
 'knee',
 'extension',
 'lateral',
 'right',
 8.5,
 0.0,
 8.5,
 6,
 38.5,
 93.0,
 'Extensión completa de rodilla. Valores normales.'),

-- Sesión 7: Juan analiza codo de Miguel (flexión)
(7, 3, 4,
 'elbow',
 'flexion',
 'lateral',
 'left',
 142.5,
 8.2,
 134.3,
 7,
 48.0,
 91.5,
 'ROM de codo normal. Práctica de medición con MediaPipe.'),

-- Sesión 8: Laura analiza hombro de Carolina (rotación externa) - Tesis
(8, 4, 5,
 'shoulder',
 'external_rotation',
 'frontal',
 'right',
 95.5,
 12.5,
 83.0,
 8,
 68.0,
 94.5,
 'Rotación externa excepcional. Datos importantes para análisis biomecánico de danza.'),

-- Sesión 9: Carlos analiza tobillo de Roberto (dorsiflexión)
(9, 5, 2,
 'ankle',
 'dorsiflexion',
 'lateral',
 'right',
 105.2,
 88.0,
 17.2,
 4,
 40.0,
 85.0,
 'ROM reducido en sujeto sedentario. Comparación con SUJ-2024-0001 para estudio.'),

-- Sesión 10: María realiza análisis bilateral de rodilla
(10, 2, 3,
 'knee',
 'flexion',
 'lateral',
 'bilateral',
 138.5,
 4.8,
 133.7,
 10,
 85.0,
 96.0,
 'Análisis bilateral. Excelente simetría entre ambas rodillas.');

-- ============================================================================
-- MEDICIONES DE ÁNGULOS (Frame-by-Frame - Muestra)
-- ============================================================================

-- Mediciones de la Sesión 1 (Carlos - Tobillo - Dorsiflexión)
INSERT INTO angle_measurement (session_id, timestamp, frame_number, angle_value, confidence) VALUES
(1, 0.0, 0, 85.2, 0.98),
(1, 0.5, 15, 88.5, 0.97),
(1, 1.0, 30, 92.3, 0.99),
(1, 1.5, 45, 96.8, 0.98),
(1, 2.0, 60, 102.5, 0.99),
(1, 2.5, 75, 107.2, 0.97),
(1, 3.0, 90, 110.5, 0.98),
(1, 3.5, 105, 108.8, 0.99),
(1, 4.0, 120, 104.2, 0.98),
(1, 4.5, 135, 98.5, 0.97);

-- Mediciones de la Sesión 2 (María - Rodilla - Flexión)
INSERT INTO angle_measurement (session_id, timestamp, frame_number, angle_value, confidence) VALUES
(2, 0.0, 0, 5.2, 0.99),
(2, 0.8, 24, 18.5, 0.98),
(2, 1.6, 48, 35.8, 0.99),
(2, 2.4, 72, 58.2, 0.97),
(2, 3.2, 96, 82.5, 0.98),
(2, 4.0, 120, 105.8, 0.99),
(2, 4.8, 144, 122.5, 0.98),
(2, 5.6, 168, 132.8, 0.99),
(2, 6.4, 192, 135.8, 0.98),
(2, 7.2, 216, 128.5, 0.97);

-- Mediciones de la Sesión 4 (Laura - Cadera - Flexión - TESIS)
INSERT INTO angle_measurement (session_id, timestamp, frame_number, angle_value, confidence) VALUES
(4, 0.0, 0, 8.5, 0.99),
(4, 1.0, 30, 22.5, 0.98),
(4, 2.0, 60, 45.8, 0.99),
(4, 3.0, 90, 68.5, 0.98),
(4, 4.0, 120, 88.2, 0.99),
(4, 5.0, 150, 105.5, 0.98),
(4, 6.0, 180, 118.8, 0.99),
(4, 7.0, 210, 125.5, 0.98),
(4, 8.0, 240, 122.2, 0.99),
(4, 9.0, 270, 112.5, 0.97);

-- ============================================================================
-- LOGS DEL SISTEMA (Actividad de estudiantes)
-- ============================================================================

INSERT INTO system_log (user_id, action, details, ip_address, timestamp) VALUES
-- Actividad del administrador - CREACIÓN DE USUARIOS
(1, 'login', 'Inicio de sesión exitoso', '192.168.1.100', '2024-11-01 08:30:00'),
(1, 'create_user', 'Usuario estudiante creado: carlos.mendez (EST-2021-0145)', '192.168.1.100', '2024-11-01 08:35:00'),
(1, 'create_user', 'Usuario estudiante creado: maria.rodriguez (EST-2022-0089)', '192.168.1.100', '2024-11-01 08:40:00'),
(1, 'create_user', 'Usuario estudiante creado: juan.garcia (EST-2022-0234)', '192.168.1.100', '2024-11-01 08:45:00'),
(1, 'create_user', 'Usuario estudiante creado: laura.martinez (EST-2020-0056)', '192.168.1.100', '2024-11-01 08:50:00'),

-- Actividad de Carlos (estudiante biomédica)
(2, 'login', 'Inicio de sesión exitoso', '192.168.1.105', '2024-11-05 14:20:00'),
(2, 'create_subject', 'Sujeto registrado: SUJ-2024-0001 (Pedro González)', '192.168.1.105', '2024-11-05 14:25:00'),
(2, 'start_analysis', 'Análisis iniciado: Tobillo - Dorsiflexión', '192.168.1.105', '2024-11-05 14:30:00'),
(2, 'save_session', 'Sesión guardada: ID 1 - ROM: 25.3°', '192.168.1.105', '2024-11-05 14:35:00'),
(2, 'export_pdf', 'Reporte exportado: Sesión #1', '192.168.1.105', '2024-11-05 14:40:00'),

-- Actividad de María (estudiante fisioterapia)
(3, 'login', 'Inicio de sesión exitoso', '192.168.1.108', '2024-11-06 10:15:00'),
(3, 'create_subject', 'Sujeto registrado: SUJ-2024-0002 (Ana Martínez)', '192.168.1.108', '2024-11-06 10:20:00'),
(3, 'start_analysis', 'Análisis iniciado: Rodilla - Flexión', '192.168.1.108', '2024-11-06 10:25:00'),
(3, 'save_session', 'Sesión guardada: ID 2 - ROM: 130.6°', '192.168.1.108', '2024-11-06 10:45:00'),

-- Actividad de Juan (estudiante kinesiología)
(4, 'login', 'Inicio de sesión exitoso', '192.168.1.112', '2024-11-07 15:00:00'),
(4, 'create_subject', 'Sujeto registrado: SUJ-2024-0003 (Miguel Torres)', '192.168.1.112', '2024-11-07 15:10:00'),
(4, 'start_analysis', 'Análisis iniciado: Hombro - Abducción', '192.168.1.112', '2024-11-07 15:15:00'),

-- Actividad de Laura (tesista)
(5, 'login', 'Inicio de sesión exitoso', '192.168.1.115', '2024-11-08 09:00:00'),
(5, 'create_subject', 'Sujeto registrado: SUJ-2024-0004 (Carolina Ramírez) - TESIS', '192.168.1.115', '2024-11-08 09:10:00'),
(5, 'start_analysis', 'Análisis iniciado: Cadera - Flexión - Datos de Tesis', '192.168.1.115', '2024-11-08 09:30:00'),
(5, 'save_session', 'Sesión guardada: ID 4 - ROM: 117.0° - CALIDAD 97%', '192.168.1.115', '2024-11-08 10:15:00'),
(5, 'export_pdf', 'Reporte exportado para tesis: Sesión #4', '192.168.1.115', '2024-11-08 10:20:00'),

-- Consultas de estadísticas
(2, 'view_statistics', 'Consulta de estadísticas de tobillo', '192.168.1.105', '2024-11-10 11:00:00'),
(3, 'view_statistics', 'Consulta de estadísticas de rodilla', '192.168.1.108', '2024-11-10 11:30:00'),
(5, 'export_data', 'Exportación de datos para análisis en SPSS - TESIS', '192.168.1.115', '2024-11-11 14:00:00');

-- ============================================================================
-- ACTUALIZACIÓN DE LAST_LOGIN
-- ============================================================================

UPDATE user SET last_login = '2024-11-14 08:30:00' WHERE id = 1;
UPDATE user SET last_login = '2024-11-12 14:20:00' WHERE id = 2;
UPDATE user SET last_login = '2024-11-13 10:15:00' WHERE id = 3;
UPDATE user SET last_login = '2024-11-11 15:00:00' WHERE id = 4;
UPDATE user SET last_login = '2024-11-14 09:00:00' WHERE id = 5;

-- ============================================================================
-- COMENTARIOS FINALES
-- ============================================================================

-- DATOS DE PRUEBA CREADOS:
-- 
-- ✅ 5 USUARIOS:
--    • 1 Administrador (admin) - Auto-creado, sin altura
--    • 4 Estudiantes de diferentes programas y semestres - CREADOS POR ADMIN
--
-- 🔒 RESTRICCIÓN DE SEGURIDAD:
--    • Solo el ADMINISTRADOR puede crear usuarios estudiantes
--    • Campo created_by registra qué admin creó cada estudiante
--    • Primer admin tiene created_by = NULL (auto-creado)
--
-- 🔬 DATOS ANTROPOMÉTRICOS (Drillis & Contini):
--    • Carlos: 175.0 cm  → Muslo: 42.9cm, Pierna: 43.1cm, Brazo: 32.6cm
--    • María:  162.0 cm  → Muslo: 39.7cm, Pierna: 39.9cm, Brazo: 30.1cm
--    • Juan:   180.0 cm  → Muslo: 44.1cm, Pierna: 44.3cm, Brazo: 33.5cm
--    • Laura:  168.0 cm  → Muslo: 41.2cm, Pierna: 41.3cm, Brazo: 31.2cm
--
-- ✅ 5 SUJETOS DE ESTUDIO:
--    • Con diferentes niveles de actividad física
--    • Registrados por diferentes estudiantes
--
-- ✅ 10 SESIONES ROM:
--    • Diferentes segmentos (tobillo, rodilla, hombro, cadera, codo)
--    • Diferentes tipos de movimiento
--    • Vistas laterales y frontales
--
-- ✅ 30 MEDICIONES DE ÁNGULOS:
--    • Frame-by-frame de 3 sesiones representativas
--    • Datos realistas con confianza >0.97
--
-- ✅ 25 LOGS DEL SISTEMA:
--    • Actividad completa de estudiantes
--    • Trazabilidad de acciones académicas
--    • 4 logs de creación de usuarios por admin
--
-- CREDENCIALES DE PRUEBA:
-- • admin / test123 (Administrador - Puede crear usuarios)
-- • carlos.mendez / test123 (Ing. Biomédica - Semestre 8 - Altura: 175cm)
-- • maria.rodriguez / test123 (Fisioterapia - Semestre 6 - Altura: 162cm)
-- • juan.garcia / test123 (Kinesiología - Semestre 5 - Altura: 180cm)
-- • laura.martinez / test123 (Ing. Biomédica - Semestre 10 - TESISTA - Altura: 168cm)
--
-- ⚠️  IMPORTANTE: 
--    • Cambiar contraseñas en producción
--    • Solo admin puede crear nuevos usuarios estudiantes
--    • Altura es OBLIGATORIA para cálculos de Drillis & Contini
-- ============================================================================
