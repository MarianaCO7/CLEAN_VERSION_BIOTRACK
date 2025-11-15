"""
🚀 APLICACIÓN PRINCIPAL FLASK - BIOTRACK
=========================================
Factory pattern para crear y configurar la aplicación Flask

RESPONSABILIDADES:
- Configurar Flask app desde config.py
- Inicializar database_manager
- Registrar blueprints (auth, main, api)
- Configurar logging (archivos + consola)
- Manejadores de errores (404, 403, 500)
- Filtros y contexto para Jinja2
- Cleanup de ESP32 al cerrar

Autor: BIOTRACK Team
Fecha: 2025-11-14
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from werkzeug.exceptions import HTTPException

# Agregar el directorio raíz al path para imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Imports locales
from app.config import get_config, create_directories
from database.database_manager import get_db_manager


# ============================================================================
# FUNCIÓN FACTORY PRINCIPAL
# ============================================================================

def create_app(config_name='development'):
    """
    Factory para crear la aplicación Flask
    
    Args:
        config_name: 'development', 'production', 'testing'
    
    Returns:
        Aplicación Flask configurada
    """
    
    # Crear aplicación Flask
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static',
                instance_relative_config=False)
    
    # ========================================================================
    # 1. CARGAR CONFIGURACIÓN
    # ========================================================================
    
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    
    print(f"🔧 Configuración cargada: {config_name}")
    
    # ========================================================================
    # 2. CREAR DIRECTORIOS NECESARIOS
    # ========================================================================
    
    try:
        create_directories()
    except Exception as e:
        print(f"⚠️  Advertencia al crear directorios: {e}")
    
    # ========================================================================
    # 3. CONFIGURAR LOGGING
    # ========================================================================
    
    setup_logging(app)
    
    # ========================================================================
    # 4. INICIALIZAR DATABASE MANAGER
    # ========================================================================
    
    try:
        db_manager = get_db_manager(app.config['DATABASE_PATH'])
        
        if db_manager.test_connection():
            app.logger.info("✅ Conexión a base de datos exitosa")
            
            # Guardar db_manager en app.config para acceso global
            app.config['DB_MANAGER'] = db_manager
        else:
            app.logger.error("❌ Error de conexión a base de datos")
            
    except Exception as e:
        app.logger.error(f"❌ Error al inicializar database manager: {e}")
    
    # ========================================================================
    # 5. REGISTRAR BLUEPRINTS
    # ========================================================================
    
    register_blueprints(app)
    
    # ========================================================================
    # 6. CONFIGURAR MANEJADORES DE ERRORES
    # ========================================================================
    
    register_error_handlers(app)
    
    # ========================================================================
    # 7. REGISTRAR FILTROS JINJA2
    # ========================================================================
    
    register_template_filters(app)
    
    # ========================================================================
    # 8. REGISTRAR CONTEXT PROCESSORS
    # ========================================================================
    
    register_context_processors(app)
    
    # ========================================================================
    # 9. CONFIGURAR HOOKS DE APLICACIÓN
    # ========================================================================
    
    register_app_hooks(app)
    
    # ========================================================================
    # 10. RUTAS PRINCIPALES (fuera de blueprints)
    # ========================================================================
    
    @app.route('/')
    def index():
        """Ruta raíz - Redirige según autenticación"""
        if 'user_id' in session:
            return redirect(url_for('main.dashboard'))
        return redirect(url_for('auth.login'))
    
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        db_manager = app.config.get('DB_MANAGER')
        
        try:
            db_healthy = db_manager.test_connection() if db_manager else False
            db_info = db_manager.get_database_info() if db_healthy else {}
            
            return jsonify({
                'status': 'healthy' if db_healthy else 'unhealthy',
                'app_name': app.config['APP_NAME'],
                'version': app.config['VERSION'],
                'database': {
                    'connected': db_healthy,
                    'info': db_info
                },
                'timestamp': datetime.utcnow().isoformat()
            }), 200 if db_healthy else 503
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    
    # ========================================================================
    # FINALIZACIÓN
    # ========================================================================
    
    app.logger.info(f"✅ Aplicación BIOTRACK creada exitosamente")
    app.logger.info(f"🏃 Modo: {config_name}")
    app.logger.info(f"🗄️  Base de datos: {app.config['DATABASE_PATH']}")
    
    return app


# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================

def setup_logging(app):
    """Configura el sistema de logging"""
    
    if not app.debug and not app.testing:
        # Crear directorio de logs si no existe
        log_dir = Path(app.config['LOG_DIR'])
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar formato
        formatter = logging.Formatter(app.config['LOG_FORMAT'])
        
        # Handler para archivo principal
        file_handler = RotatingFileHandler(
            app.config['LOG_FILE'],
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        
        # Handler para errores
        error_handler = RotatingFileHandler(
            app.config['ERROR_LOG_FILE'],
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        
        # Agregar handlers
        app.logger.addHandler(file_handler)
        app.logger.addHandler(error_handler)
    
    # Handler para consola (siempre)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '[%(levelname)s] %(message)s'
    ))
    app.logger.addHandler(console_handler)
    
    # Configurar nivel
    app.logger.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
    
    app.logger.info("📝 Sistema de logging configurado")


# ============================================================================
# REGISTRO DE BLUEPRINTS
# ============================================================================

def register_blueprints(app):
    """Registra todos los blueprints de la aplicación"""
    
    try:
        # Blueprint de autenticación
        from app.routes.auth import auth_bp
        app.register_blueprint(auth_bp)
        app.logger.info("✅ Blueprint 'auth' registrado")
        
    except Exception as e:
        app.logger.warning(f"⚠️  No se pudo registrar blueprint 'auth': {e}")
    
    try:
        # Blueprint principal (dashboard, etc.)
        from app.routes.main import main_bp
        app.register_blueprint(main_bp)
        app.logger.info("✅ Blueprint 'main' registrado")
        
    except Exception as e:
        app.logger.warning(f"⚠️  No se pudo registrar blueprint 'main': {e}")
    
    try:
        # Blueprint de API
        from app.routes.api import api_bp
        app.register_blueprint(api_bp, url_prefix='/api')
        app.logger.info("✅ Blueprint 'api' registrado")
        
    except Exception as e:
        app.logger.warning(f"⚠️  No se pudo registrar blueprint 'api': {e}")


# ============================================================================
# MANEJADORES DE ERRORES
# ============================================================================

def register_error_handlers(app):
    """Registra manejadores de errores personalizados"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Página no encontrada"""
        app.logger.warning(f"404 Error: {request.url}")
        
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Recurso no encontrado'}), 404
        
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Acceso prohibido"""
        app.logger.warning(f"403 Error: {request.url}")
        
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Acceso prohibido'}), 403
        
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(500)
    def internal_error(error):
        """Error interno del servidor"""
        app.logger.error(f"500 Error: {error}")
        
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Error interno del servidor'}), 500
        
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Maneja excepciones no capturadas"""
        
        # Log del error
        app.logger.error(f"Excepción no capturada: {error}", exc_info=True)
        
        # Si es un error HTTP, dejarlo pasar
        if isinstance(error, HTTPException):
            return error
        
        # Error genérico
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Error inesperado'}), 500
        
        return render_template('errors/500.html'), 500
    
    app.logger.info("✅ Manejadores de errores registrados")


# ============================================================================
# FILTROS JINJA2
# ============================================================================

def register_template_filters(app):
    """Registra filtros personalizados para Jinja2"""
    
    @app.template_filter('datetime')
    def format_datetime(value, format='%d/%m/%Y %H:%M'):
        """Formatea datetime"""
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except:
                return value
        return value.strftime(format)
    
    @app.template_filter('date')
    def format_date(value, format='%d/%m/%Y'):
        """Formatea fecha"""
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except:
                return value
        return value.strftime(format)
    
    @app.template_filter('round')
    def round_number(value, decimals=2):
        """Redondea número"""
        if value is None:
            return 0
        return round(float(value), decimals)
    
    app.logger.info("✅ Filtros de template registrados")


# ============================================================================
# CONTEXT PROCESSORS
# ============================================================================

def register_context_processors(app):
    """Registra variables globales para todos los templates"""
    
    @app.context_processor
    def inject_globals():
        """Inyecta variables globales en templates"""
        return {
            'app_name': app.config['APP_NAME'],
            'app_version': app.config['VERSION'],
            'current_year': datetime.now().year,
            'segments': app.config['AVAILABLE_SEGMENTS'],
            'camera_views': app.config['CAMERA_VIEWS']
        }
    
    @app.context_processor
    def inject_user():
        """Inyecta información del usuario actual"""
        current_user = None
        
        if 'user_id' in session:
            try:
                db_manager = app.config.get('DB_MANAGER')
                if db_manager:
                    current_user = db_manager.get_user_by_id(session['user_id'])
            except:
                pass
        
        return {'current_user': current_user}
    
    app.logger.info("✅ Context processors registrados")


# ============================================================================
# HOOKS DE APLICACIÓN
# ============================================================================

def register_app_hooks(app):
    """Registra hooks de ciclo de vida de la aplicación"""
    
    @app.before_request
    def before_request():
        """Se ejecuta antes de cada request"""
        # Logging de requests (solo en desarrollo)
        if app.debug:
            app.logger.debug(f"{request.method} {request.path}")
    
    @app.after_request
    def after_request(response):
        """Se ejecuta después de cada request"""
        # Headers de seguridad
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response
    
    @app.teardown_appcontext
    def cleanup_esp32(exception=None):
        """Limpieza de conexiones ESP32 al cerrar"""
        # TODO: Implementar limpieza de ESP32 si está conectado
        pass
    
    app.logger.info("✅ Hooks de aplicación registrados")


# ============================================================================
# PUNTO DE ENTRADA (si se ejecuta directamente)
# ============================================================================

if __name__ == '__main__':
    # Crear aplicación
    app = create_app('development')
    
    # Ejecutar servidor
    print("\n" + "=" * 70)
    print("🏃 BIOTRACK - Sistema de Análisis Biomecánico Educativo")
    print("=" * 70)
    print(f"📍 URL: http://localhost:5000")
    print(f"🔑 Usuarios de prueba:")
    print(f"   • admin / test123 (Administrador)")
    print(f"   • carlos.mendez / test123 (Estudiante)")
    print("=" * 70)
    print("\n💡 Presiona Ctrl+C para detener el servidor\n")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True
    )
