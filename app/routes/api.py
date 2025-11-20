"""
🔌 BLUEPRINT DE API - BIOTRACK
===============================
Endpoints JSON para comunicación AJAX y REST

ENDPOINTS:
- /api/user/stats: Estadísticas del usuario
- /api/sessions/<id>: Obtener sesión ROM
- /api/subjects: CRUD de sujetos
- /api/rom-session: Crear/actualizar sesión ROM
- /api/video_feed: Stream MJPEG de video procesado (NUEVO)
- /api/analysis/start: Iniciar análisis (NUEVO)
- /api/analysis/stop: Detener análisis (NUEVO)
- /api/analysis/current_data: Obtener datos actuales (NUEVO)

Autor: BIOTRACK Team
Fecha: 2025-11-14
"""

from flask import (
    Blueprint, jsonify, request, session, current_app, Response
)
from app.routes.auth import login_required
import cv2
import numpy as np
import logging
import time

# Crear blueprint
api_bp = Blueprint('api', __name__)

# Logger para uso fuera del contexto de Flask
logger = logging.getLogger(__name__)

# ============================================================================
# CACHE GLOBAL DE ANALYZERS
# ============================================================================
# Diccionario para cachear analyzers por tipo (evita re-inicialización de 25s)
_ANALYZER_CACHE = {}

# Variable global para el analyzer actual (compartida entre requests)
current_analyzer = None

def get_cached_analyzer(analyzer_type: str, analyzer_class):
    """
    Obtiene analyzer cacheado o crea uno nuevo
    
    Primera llamada: Inicializa MediaPipe (~25 segundos)
    Siguientes llamadas: Reutiliza analyzer cacheado (0 segundos)
    
    Args:
        analyzer_type: Tipo de analyzer ('shoulder_profile', 'shoulder_frontal', etc.)
        analyzer_class: Clase del analyzer a instanciar
    
    Returns:
        Analyzer inicializado y listo para usar
    """
    if analyzer_type not in _ANALYZER_CACHE:
        logger.info(f"🔧 Creando NUEVO analyzer '{analyzer_type}' - Primera inicialización (~25s)")
        _ANALYZER_CACHE[analyzer_type] = analyzer_class(
            processing_width=640,
            processing_height=480,
            show_skeleton=False
        )
        logger.info(f"✅ Analyzer '{analyzer_type}' listo y cacheado")
    else:
        logger.info(f"⚡ Reutilizando analyzer cacheado '{analyzer_type}' (0s)")
    
    return _ANALYZER_CACHE[analyzer_type]


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


# ============================================================================
# VIDEO STREAMING Y ANÁLISIS EN VIVO (NUEVO)
# ============================================================================

@api_bp.route('/video_feed')
@login_required
def video_feed():
    """
    Stream MJPEG de video procesado con MediaPipe
    
    Este endpoint genera un stream continuo de frames procesados
    por el analyzer correspondiente al ejercicio activo.
    
    Returns:
        Response: Stream MJPEG multipart
    """
    from hardware.camera_manager import camera_manager
    from app.analyzers import ShoulderProfileAnalyzer, ShoulderFrontalAnalyzer
    
    # ⚠️ CRÍTICO: Capturar valores de session ANTES del generador
    # (el generador se ejecuta fuera del request context)
    analyzer_type = session.get('analyzer_type')
    user_id = session.get('user_id')
    
    def generate_frames():
        global current_analyzer
        
        if not analyzer_type or not user_id:
            # Frame de error
            error_frame = _create_error_frame("No hay ejercicio activo. Selecciona un ejercicio primero.")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n')
            return
        
        # Mapa de analyzers
        analyzer_classes = {
            'shoulder_profile': ShoulderProfileAnalyzer,
            'shoulder_frontal': ShoulderFrontalAnalyzer,
            # Agregar más analyzers aquí en el futuro
        }
        
        # Inicializar analyzer si no existe o es diferente
        analyzer_class = analyzer_classes.get(analyzer_type)
        if not analyzer_class:
            error_frame = _create_error_frame(f"Analyzer '{analyzer_type}' no implementado aún")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n')
            return
        
        # Obtener analyzer cacheado (reutiliza si ya existe)
        current_analyzer = get_cached_analyzer(analyzer_type, analyzer_class)
        
        # Adquirir cámara (context manager automático)
        try:
            with camera_manager.acquire_camera(user_id=user_id, width=1280, height=720) as cap:
                logger.info(f"Cámara adquirida por '{user_id}' - Iniciando stream")
                
                frame_count = 0
                mediapipe_ready = False
                
                while True:
                    ret, frame = cap.read()
                    
                    if not ret:
                        logger.warning("No se pudo leer frame de la cámara")
                        break
                    
                    frame_count += 1
                    
                    # Verificar si MediaPipe está listo
                    if not mediapipe_ready:
                        # Chequear si el pose model ya se inicializó
                        mediapipe_ready = hasattr(current_analyzer, 'pose') and current_analyzer.pose is not None
                        
                        if not mediapipe_ready:
                            # MediaPipe AÚN inicializando - Mostrar frame CRUDO (sin procesar)
                            # Esto da feedback visual inmediato al usuario (ve su cámara en ~2s)
                            if frame_count % 30 == 0:  # Log cada 30 frames (~1 segundo)
                                logger.debug(f"⏳ MediaPipe inicializando... Frame {frame_count}")
                            
                            # Frame crudo con overlay de "Cargando..."
                            raw_frame = frame.copy()
                            cv2.putText(
                                raw_frame,
                                "Inicializando MediaPipe...",
                                (50, 50),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.8,
                                (0, 255, 255),  # Amarillo
                                2
                            )
                            cv2.putText(
                                raw_frame,
                                "El skeleton aparecera en unos segundos",
                                (50, 90),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                (255, 255, 255),  # Blanco
                                1
                            )
                            
                            processed_frame = raw_frame
                        else:
                            # MediaPipe LISTO - Primera vez que procesamos
                            logger.info(f"✅ MediaPipe listo! Iniciando procesamiento con skeleton")
                            processed_frame = current_analyzer.process_frame(frame)
                    else:
                        # MediaPipe ya estaba listo - Procesamiento normal
                        try:
                            processed_frame = current_analyzer.process_frame(frame)
                        except Exception as e:
                            logger.error(f"Error al procesar frame: {e}")
                            processed_frame = _create_error_frame(f"Error en procesamiento: {str(e)}")
                    
                    # Codificar frame como JPEG
                    try:
                        ret_encode, buffer = cv2.imencode(
                            '.jpg', 
                            processed_frame, 
                            [cv2.IMWRITE_JPEG_QUALITY, 70]  # 70% calidad (optimizado para velocidad)
                        )
                        
                        if not ret_encode:
                            logger.error("Error al codificar frame")
                            continue
                        
                        frame_bytes = buffer.tobytes()
                        
                        # Yield del frame en formato MJPEG
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    
                    except Exception as e:
                        logger.error(f"Error al codificar/enviar frame: {e}")
                        continue
        
        except GeneratorExit:
            # Usuario cerró el navegador/tab
            logger.info(f"Stream cerrado por usuario '{user_id}' (GeneratorExit)")
        
        except RuntimeError as e:
            # Cámara en uso o no disponible
            logger.error(f"RuntimeError en video_feed: {e}")
            error_frame = _create_error_frame(str(e))
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n')
        
        except Exception as e:
            # Error inesperado
            logger.error(f"Error inesperado en video_feed: {e}", exc_info=True)
            error_frame = _create_error_frame(f"Error inesperado: {str(e)}")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n')
        
        finally:
            # Cleanup siempre se ejecuta
            logger.info(f"Finalizando stream para usuario '{user_id}'")
    
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@api_bp.route('/analysis/start', methods=['POST'])
@login_required
def start_analysis():
    """
    Marca el inicio de una sesión de análisis
    
    Body JSON:
        {
            "segment_type": "shoulder",
            "exercise_key": "flexion"
        }
    
    Returns:
        JSON con estado
    """
    try:
        data = request.get_json() or {}
        
        segment_type = data.get('segment_type')
        exercise_key = data.get('exercise_key')
        
        if not segment_type or not exercise_key:
            return jsonify({
                'success': False,
                'error': 'Faltan parámetros: segment_type y exercise_key'
            }), 400
        
        # Guardar en sesión
        session['analysis_active'] = True
        session['analysis_start_time'] = time.time()
        
        current_app.logger.info(
            f"Análisis iniciado: {segment_type}/{exercise_key} "
            f"por usuario {session.get('user_id')}"
        )
        
        return jsonify({
            'success': True,
            'message': 'Análisis iniciado correctamente',
            'segment_type': segment_type,
            'exercise_key': exercise_key
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error al iniciar análisis: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/analysis/stop', methods=['POST'])
@login_required
def stop_analysis():
    """
    Detiene la sesión de análisis actual
    
    Returns:
        JSON con estado y datos finales
    """
    global current_analyzer
    
    try:
        # Obtener datos finales del analyzer
        final_data = {}
        if current_analyzer:
            final_data = current_analyzer.get_current_data()
        
        # Limpiar sesión
        session['analysis_active'] = False
        session.pop('analysis_start_time', None)
        
        current_app.logger.info(
            f"Análisis detenido por usuario {session.get('user_id')} | "
            f"ROM final: {final_data.get('max_rom', 'N/A')}"
        )
        
        return jsonify({
            'success': True,
            'message': 'Análisis detenido correctamente',
            'final_data': final_data
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error al detener análisis: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/analysis/current_data', methods=['GET'])
@login_required
def get_current_data():
    """
    Obtiene los datos actuales del análisis en tiempo real
    
    Polling endpoint - el frontend puede llamar cada 100-200ms
    
    Returns:
        JSON con datos actuales del analyzer
    """
    global current_analyzer
    
    try:
        if current_analyzer is None:
            return jsonify({
                'success': False,
                'error': 'No hay analyzer activo',
                'data': {}
            }), 200  # No es error 500, solo no hay datos
        
        # Obtener datos del analyzer
        data = current_analyzer.get_current_data()
        
        return jsonify({
            'success': True,
            'data': data,
            'timestamp': request.timestamp
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error al obtener datos actuales: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {}
        }), 500


@api_bp.route('/analysis/reset', methods=['POST'])
@login_required
def reset_analysis():
    """
    Reinicia las estadísticas del analyzer (ROM máximo, ángulos, etc.)
    sin recrear el analyzer completo
    
    Returns:
        JSON con estado
    """
    global current_analyzer
    
    try:
        if current_analyzer is None:
            return jsonify({
                'success': False,
                'error': 'No hay analyzer activo'
            }), 400
        
        # Resetear analyzer
        current_analyzer.reset()
        
        current_app.logger.info(f"Analyzer reseteado por usuario {session.get('user_id')}")
        
        return jsonify({
            'success': True,
            'message': 'Estadísticas reiniciadas correctamente'
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error al resetear analyzer: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _create_error_frame(message: str) -> bytes:
    """
    Crea un frame de error con mensaje
    
    Args:
        message: Mensaje de error a mostrar
    
    Returns:
        bytes: Frame codificado como JPEG
    """
    # Crear frame negro con texto
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Agregar texto (dividir en líneas si es muy largo)
    words = message.split()
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if len(test_line) > 35:  # ~35 caracteres por línea
            lines.append(current_line)
            current_line = word
        else:
            current_line = test_line
    
    if current_line:
        lines.append(current_line)
    
    # Dibujar líneas centradas
    y_start = 240 - (len(lines) * 15)  # Centrar verticalmente
    for i, line in enumerate(lines):
        y_pos = y_start + (i * 30)
        cv2.putText(
            frame, 
            line, 
            (50, y_pos), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            (0, 0, 255),  # Rojo
            2
        )
    
    # Codificar como JPEG
    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buffer.tobytes()
