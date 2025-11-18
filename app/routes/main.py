"""
🏠 BLUEPRINT PRINCIPAL - BIOTRACK
==================================
Rutas principales de la aplicación

RUTAS:
- /dashboard: Dashboard del usuario
- /profile: Perfil del usuario
- /subjects: Gestión de sujetos
- /sessions: Historial de sesiones
- /users: Gestión de usuarios (admin)

Autor: BIOTRACK Team
Fecha: 2025-11-14
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, session, current_app
)
from app.routes.auth import login_required, admin_required
from hardware.camera_manager import camera_manager, check_camera_availability

# Crear blueprint
main_bp = Blueprint('main', __name__)


# ============================================================================
# DASHBOARD
# ============================================================================

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Dashboard principal del usuario
    Redirige al dashboard específico según el rol
    """
    
    db_manager = current_app.config.get('DB_MANAGER')
    user_id = session.get('user_id')
    user_role = session.get('role')
    
    # Obtener estadísticas del usuario
    stats = db_manager.get_user_statistics(user_id)
    
    # Obtener sesiones recientes
    recent_sessions = db_manager.get_sessions_by_user(user_id)
    recent_sessions = recent_sessions[:5] if recent_sessions else []
    
    # Redirigir según rol
    if user_role == 'admin':
        return render_template(
            'admin/dashboard.html',
            stats=stats,
            recent_sessions=recent_sessions
        )
    else:
        return render_template(
            'user/dashboard.html',
            stats=stats,
            recent_sessions=recent_sessions
        )


# ============================================================================
# PERFIL
# ============================================================================

@main_bp.route('/profile')
@login_required
def profile():
    """
    Perfil del usuario actual
    """
    
    db_manager = current_app.config.get('DB_MANAGER')
    user = db_manager.get_user_by_id(session.get('user_id'))
    
    return render_template('profile.html', user=user)


# ============================================================================
# SUJETOS
# ============================================================================

@main_bp.route('/subjects')
@login_required
def subjects():
    """
    Lista de sujetos del usuario
    """
    
    db_manager = current_app.config.get('DB_MANAGER')
    user_id = session.get('user_id')
    
    # Si es admin, ver todos; si es student, solo los suyos
    if session.get('role') == 'admin':
        subjects_list = db_manager.get_all_subjects()
    else:
        subjects_list = db_manager.get_subjects_by_user(user_id)
    
    return render_template('subjects/list.html', subjects=subjects_list)


# ============================================================================
# SESIONES / HISTORIAL
# ============================================================================

@main_bp.route('/sessions')
@login_required
def sessions():
    """
    Historial de sesiones ROM del usuario
    """
    
    db_manager = current_app.config.get('DB_MANAGER')
    user_id = session.get('user_id')
    
    sessions_list = db_manager.get_sessions_by_user(user_id)
    
    return render_template('history/list.html', sessions=sessions_list)


# ============================================================================
# SEGMENTOS BIOMECÁNICOS
# ============================================================================

@main_bp.route('/segments')
@login_required
def segments():
    """
    Página de selección de segmentos biomecánicos
    """
    return render_template('components/segments.html')


@main_bp.route('/segments/<segment_type>/exercises')
@login_required
def segment_exercises(segment_type):
    """
    Página de selección de ejercicios para un segmento específico
    """
    
    # Configuración de segmentos
    segments_config = {
        'shoulder': {
            'name': 'Hombro',
            'description': 'Flexión, extensión, abducción y rotación glenohumeral',
            'icon': 'shoulder_1.png',
            'exercises': [
                {
                    'key': 'flexion',
                    'name': 'Flexión de Hombro',
                    'view': 'Lateral',
                    'view_icon': 'person-standing',
                    'difficulty': 'easy',
                    'difficulty_label': 'Fácil',
                    'rom_range': '0° - 180°',
                    'repetitions': '3-5',
                    'speed': 'Lenta y controlada',
                    'instructions': 'Levanta el brazo hacia adelante hasta alcanzar la máxima altura posible, manteniendo el codo extendido.',
                    'has_video': True,
                    'duration': '15',
                    'warning': None
                },
                {
                    'key': 'extension',
                    'name': 'Extensión de Hombro',
                    'view': 'Lateral',
                    'view_icon': 'person-standing',
                    'difficulty': 'easy',
                    'difficulty_label': 'Fácil',
                    'rom_range': '0° - 60°',
                    'repetitions': '3-5',
                    'speed': 'Lenta y controlada',
                    'instructions': 'Lleva el brazo hacia atrás desde la posición neutra, manteniendo el codo extendido y el torso erguido.',
                    'has_video': True,
                    'duration': '12',
                    'warning': 'No fuerces el movimiento más allá de tu rango cómodo'
                },
                {
                    'key': 'abduction',
                    'name': 'Abducción de Hombro',
                    'view': 'Frontal',
                    'view_icon': 'diagram-3',
                    'difficulty': 'easy',
                    'difficulty_label': 'Fácil',
                    'rom_range': '0° - 180°',
                    'repetitions': '3-5',
                    'speed': 'Lenta y controlada',
                    'instructions': 'Levanta el brazo lateralmente desde la posición neutra hasta alcanzar la vertical.',
                    'has_video': True,
                    'duration': '15',
                    'warning': None
                }
            ]
        },
        'elbow': {
            'name': 'Codo',
            'description': 'Flexión, extensión y movimientos de pronación-supinación',
            'icon': 'elbow_1.png',
            'exercises': [
                {
                    'key': 'flexion',
                    'name': 'Flexión de Codo',
                    'view': 'Lateral',
                    'view_icon': 'person-standing',
                    'difficulty': 'easy',
                    'difficulty_label': 'Fácil',
                    'rom_range': '0° - 145°',
                    'repetitions': '3-5',
                    'speed': 'Moderada',
                    'instructions': 'Flexiona el codo llevando la mano hacia el hombro, manteniendo el brazo estable.',
                    'has_video': True,
                    'duration': '10',
                    'warning': None
                }
            ]
        },
        'hip': {
            'name': 'Cadera',
            'description': 'Flexión, extensión, abducción y rotación de cadera',
            'icon': 'hips_1.png',
            'exercises': [
                {
                    'key': 'flexion',
                    'name': 'Flexión de Cadera',
                    'view': 'Lateral',
                    'view_icon': 'person-standing',
                    'difficulty': 'medium',
                    'difficulty_label': 'Medio',
                    'rom_range': '0° - 120°',
                    'repetitions': '3-5',
                    'speed': 'Lenta',
                    'instructions': 'Levanta la rodilla hacia el pecho manteniendo la espalda recta y el equilibrio.',
                    'has_video': True,
                    'duration': '12',
                    'warning': 'Mantén el equilibrio apoyándote si es necesario'
                },
                {
                    'key': 'abduction',
                    'name': 'Abducción de Cadera',
                    'view': 'Frontal',
                    'view_icon': 'diagram-3',
                    'difficulty': 'medium',
                    'difficulty_label': 'Medio',
                    'rom_range': '0° - 45°',
                    'repetitions': '3-5',
                    'speed': 'Lenta',
                    'instructions': 'Separa la pierna lateralmente manteniendo el cuerpo estable y la rodilla extendida.',
                    'has_video': True,
                    'duration': '12',
                    'warning': 'Usa apoyo para mantener el equilibrio'
                },
                {
                    'key': 'adduction',
                    'name': 'Aducción de Cadera',
                    'view': 'Frontal',
                    'view_icon': 'diagram-3',
                    'difficulty': 'medium',
                    'difficulty_label': 'Medio',
                    'rom_range': '0° - 30°',
                    'repetitions': '3-5',
                    'speed': 'Lenta',
                    'instructions': 'Desde una posición de pierna elevada lateralmente, lleva la pierna hacia la línea media del cuerpo cruzándola.',
                    'has_video': True,
                    'duration': '12',
                    'warning': 'Mantén la pelvis estable durante el movimiento'
                }
            ]
        },
        'knee': {
            'name': 'Rodilla',
            'description': 'Flexión y extensión de la articulación tibiofemoral',
            'icon': 'knee_1.png',
            'exercises': [
                {
                    'key': 'flexion',
                    'name': 'Flexión de Rodilla',
                    'view': 'Lateral',
                    'view_icon': 'person-standing',
                    'difficulty': 'easy',
                    'difficulty_label': 'Fácil',
                    'rom_range': '0° - 135°',
                    'repetitions': '3-5',
                    'speed': 'Moderada',
                    'instructions': 'Flexiona la rodilla llevando el talón hacia los glúteos mientras mantienes el equilibrio.',
                    'has_video': True,
                    'duration': '10',
                    'warning': 'Apóyate si sientes inestabilidad'
                }
            ]
        },
        'ankle': {
            'name': 'Tobillo',
            'description': 'Dorsiflexión, plantiflexión e inversión-eversión',
            'icon': 'ankle_1.png',
            'exercises': [
                {
                    'key': 'dorsiflexion',
                    'name': 'Dorsiflexión de Tobillo',
                    'view': 'Lateral',
                    'view_icon': 'person-standing',
                    'difficulty': 'easy',
                    'difficulty_label': 'Fácil',
                    'rom_range': '0° - 20°',
                    'repetitions': '5-8',
                    'speed': 'Lenta',
                    'instructions': 'Flexiona el pie hacia arriba llevando los dedos hacia la espinilla.',
                    'has_video': True,
                    'duration': '8',
                    'warning': None
                },
                {
                    'key': 'plantarflexion',
                    'name': 'Plantiflexión de Tobillo',
                    'view': 'Lateral',
                    'view_icon': 'person-standing',
                    'difficulty': 'easy',
                    'difficulty_label': 'Fácil',
                    'rom_range': '0° - 50°',
                    'repetitions': '5-8',
                    'speed': 'Lenta',
                    'instructions': 'Extiende el pie hacia abajo como si te pusieras de puntillas.',
                    'has_video': True,
                    'duration': '8',
                    'warning': None
                }
            ]
        }
    }
    
    # Validar que el segmento existe
    if segment_type not in segments_config:
        flash('Segmento no encontrado', 'danger')
        return redirect(url_for('main.segments'))
    
    segment = segments_config[segment_type]
    
    return render_template(
        'components/exercise_selector.html',
        segment_type=segment_type,
        segment_name=segment['name'],
        segment_description=segment['description'],
        segment_icon=segment['icon'],
        exercises=segment['exercises']
    )


# ============================================================================
# ANÁLISIS EN VIVO (NUEVO)
# ============================================================================

@main_bp.route('/segments/<segment_type>/exercises/<exercise_key>')
@login_required
def live_analysis(segment_type, exercise_key):
    """
    Página de análisis en vivo para ejercicios específicos
    
    URL ejemplos:
    - /segments/shoulder/exercises/flexion (Vista perfil)
    - /segments/shoulder/exercises/abduction (Vista frontal)
    - /segments/elbow/exercises/flexion
    - /segments/hip/exercises/flexion
    - /segments/knee/exercises/flexion
    - /segments/ankle/exercises/dorsiflexion
    """
    
    # Verificar disponibilidad de cámara ANTES de renderizar
    available, message = check_camera_availability()
    if not available:
        flash(message, 'warning')
        return redirect(url_for('main.segment_exercises', segment_type=segment_type))
    
    # Configuración completa de ejercicios
    exercises_db = {
        'shoulder': {
            'flexion': {
                'name': 'Flexión de Hombro',
                'description': 'Movimiento del brazo hacia adelante y arriba desde posición neutra',
                'camera_view': 'profile',
                'camera_view_label': 'Perfil',
                'min_angle': 0,
                'max_angle': 180,
                'analyzer_type': 'shoulder_profile',
                'analyzer_class': 'ShoulderProfileAnalyzer',
                'instructions': [
                    'Colócate de PERFIL a la cámara (lado derecho o izquierdo)',
                    'Brazo relajado junto al cuerpo (posición inicial 0°)',
                    'Levanta el brazo hacia ADELANTE lentamente',
                    'Alcanza la máxima altura posible (objetivo: 180°)',
                    'Mantén la posición máxima 2-3 segundos',
                    'Evita inclinar el tronco hacia adelante'
                ],
                'setup': [
                    'Cámara a altura del pecho',
                    'Distancia: 2-3 metros',
                    'Fondo despejado y buena iluminación',
                    'Ropa ajustada que permita ver contorno del brazo'
                ]
            },
            'abduction': {
                'name': 'Abducción de Hombro',
                'description': 'Movimiento bilateral de los brazos hacia los lados',
                'camera_view': 'frontal',
                'camera_view_label': 'Frontal',
                'min_angle': 0,
                'max_angle': 180,
                'analyzer_type': 'shoulder_frontal',
                'analyzer_class': 'ShoulderFrontalAnalyzer',
                'instructions': [
                    'Colócate de FRENTE a la cámara',
                    'Brazos relajados a los lados del cuerpo (0°)',
                    'Levanta AMBOS brazos SIMULTÁNEAMENTE hacia los lados',
                    'Alcanza la máxima altura (objetivo: 180° sobre la cabeza)',
                    'Mantén simetría entre ambos brazos',
                    'Mantén la posición máxima 2-3 segundos'
                ],
                'setup': [
                    'Cámara a altura del pecho',
                    'Distancia: 2-3 metros',
                    'Centrado en el frame',
                    'Fondo despejado y buena iluminación'
                ]
            }
        },
        # Placeholders para otros segmentos (implementar después)
        'elbow': {
            'flexion': {
                'name': 'Flexión de Codo',
                'description': 'Movimiento de cierre del antebrazo hacia el brazo',
                'camera_view': 'profile',
                'camera_view_label': 'Perfil',
                'min_angle': 0,
                'max_angle': 150,
                'analyzer_type': 'elbow_profile',
                'analyzer_class': 'ElbowProfileAnalyzer',
                'instructions': [
                    'Colócate de PERFIL a la cámara',
                    'Brazo extendido junto al cuerpo (0°)',
                    'Flexiona el codo acercando la mano al hombro',
                    'Alcanza la flexión máxima (objetivo: 150°)',
                    'Mantén el hombro estable (no lo muevas)'
                ],
                'setup': [
                    'Cámara a altura del pecho',
                    'Distancia: 2 metros',
                    'Fondo despejado'
                ]
            }
        }
    }
    
    # Validar que exista el segmento
    if segment_type not in exercises_db:
        flash(f'Segmento "{segment_type}" no encontrado', 'error')
        return redirect(url_for('main.segments'))
    
    # Validar que exista el ejercicio
    if exercise_key not in exercises_db[segment_type]:
        flash(f'Ejercicio "{exercise_key}" no encontrado en {segment_type}', 'error')
        return redirect(url_for('main.segment_exercises', segment_type=segment_type))
    
    # Obtener configuración del ejercicio
    exercise = exercises_db[segment_type][exercise_key]
    
    # Guardar en sesión para uso en video_feed
    session['current_segment'] = segment_type
    session['current_exercise'] = exercise_key
    session['analyzer_type'] = exercise['analyzer_type']
    
    return render_template(
        'measurement/live_analysis.html',
        segment_type=segment_type,
        exercise_key=exercise_key,
        exercise_name=exercise['name'],
        exercise_description=exercise['description'],
        camera_view=exercise['camera_view'],
        camera_view_label=exercise['camera_view_label'],
        min_angle=exercise['min_angle'],
        max_angle=exercise['max_angle'],
        instructions=exercise['instructions'],
        setup=exercise['setup']
    )


# ============================================================================
# GESTIÓN DE USUARIOS (Admin)
# ============================================================================

@main_bp.route('/users')
@admin_required
def users():
    """
    Lista de usuarios (solo administrador)
    """
    
    db_manager = current_app.config.get('DB_MANAGER')
    users_list = db_manager.get_all_users(active_only=False)
    
    return render_template('admin/users.html', users=users_list)
