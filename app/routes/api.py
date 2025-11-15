"""
🔌 BLUEPRINT DE API - BIOTRACK
===============================
Endpoints JSON para comunicación AJAX y REST

ENDPOINTS:
- /api/user/stats: Estadísticas del usuario
- /api/sessions/<id>: Obtener sesión ROM
- /api/subjects: CRUD de sujetos
- /api/rom-session: Crear/actualizar sesión ROM

Autor: BIOTRACK Team
Fecha: 2025-11-14
"""

from flask import (
    Blueprint, jsonify, request, session, current_app
)
from app.routes.auth import login_required

# Crear blueprint
api_bp = Blueprint('api', __name__)


# ============================================================================
# ESTADÍSTICAS
# ============================================================================

@api_bp.route('/user/stats', methods=['GET'])
@login_required
def get_user_stats():
    """
    Obtiene estadísticas del usuario actual
    
    Returns:
        JSON con estadísticas
    """
    
    db_manager = current_app.config.get('DB_MANAGER')
    user_id = session.get('user_id')
    
    try:
        stats = db_manager.get_user_statistics(user_id)
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener estadísticas: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# SESIONES ROM
# ============================================================================

@api_bp.route('/sessions/<int:session_id>', methods=['GET'])
@login_required
def get_session(session_id):
    """
    Obtiene detalles de una sesión ROM
    
    Args:
        session_id: ID de la sesión
    
    Returns:
        JSON con datos de la sesión
    """
    
    db_manager = current_app.config.get('DB_MANAGER')
    
    try:
        rom_session = db_manager.get_rom_session_by_id(session_id)
        
        if not rom_session:
            return jsonify({
                'success': False,
                'error': 'Sesión no encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'data': rom_session.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener sesión: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/rom-session', methods=['POST'])
@login_required
def create_rom_session():
    """
    Crea una nueva sesión ROM
    
    Request JSON:
        {
            "subject_id": int,
            "segment": str,
            "exercise_type": str,
            "camera_view": str,
            "side": str,
            "max_angle": float,
            "min_angle": float,
            "rom_value": float,
            "quality_score": float,
            "notes": str
        }
    
    Returns:
        JSON con sesión creada
    """
    
    db_manager = current_app.config.get('DB_MANAGER')
    user_id = session.get('user_id')
    
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        required_fields = ['subject_id', 'segment', 'exercise_type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Campo requerido: {field}'
                }), 400
        
        # Crear sesión
        rom_session = db_manager.create_rom_session(
            subject_id=data['subject_id'],
            user_id=user_id,
            segment=data['segment'],
            exercise_type=data['exercise_type'],
            camera_view=data.get('camera_view'),
            side=data.get('side'),
            max_angle=data.get('max_angle'),
            min_angle=data.get('min_angle'),
            rom_value=data.get('rom_value'),
            repetitions=data.get('repetitions', 0),
            duration=data.get('duration'),
            quality_score=data.get('quality_score'),
            notes=data.get('notes')
        )
        
        # Log de actividad
        db_manager.log_action(
            action='create_rom_session',
            user_id=user_id,
            details=f"Sesión ROM creada: {data['segment']} - {data['exercise_type']}",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'data': rom_session.to_dict()
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error al crear sesión ROM: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# INFO DEL SISTEMA
# ============================================================================

@api_bp.route('/system/info', methods=['GET'])
def system_info():
    """
    Información del sistema (no requiere auth)
    
    Returns:
        JSON con info del sistema
    """
    
    db_manager = current_app.config.get('DB_MANAGER')
    
    try:
        db_info = db_manager.get_database_info()
        
        return jsonify({
            'success': True,
            'data': {
                'app_name': current_app.config['APP_NAME'],
                'version': current_app.config['VERSION'],
                'database': db_info
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
