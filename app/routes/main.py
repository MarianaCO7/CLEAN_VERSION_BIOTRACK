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
            'icon': 'hip_1.png',
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
