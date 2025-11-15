"""
📹 CAMERA MANAGER - GESTOR SINGLETON DE CÁMARA WEB
===================================================
Gestiona el acceso exclusivo y thread-safe a la cámara web

CARACTERÍSTICAS:
- Singleton pattern (solo una instancia en toda la app)
- Thread-safe con locks para acceso concurrente
- Context manager para uso seguro (auto-release)
- Previene que múltiples sesiones usen la cámara simultáneamente
- Liberación automática de recursos incluso con errores

UBICACIÓN:
Este módulo está en hardware/ porque la cámara es infraestructura física,
al igual que ESP32. NO es un controller MVC.

Autor: BIOTRACK Team
Fecha: 2025-11-14
"""

import cv2
import threading
from contextlib import contextmanager
from typing import Optional, Generator
import logging

# Configurar logging
logger = logging.getLogger(__name__)


class CameraManager:
    """
    Singleton thread-safe para gestionar acceso exclusivo a la cámara
    
    Uso:
        camera_manager = CameraManager()
        
        with camera_manager.acquire_camera(user_id='user123') as cap:
            ret, frame = cap.read()
            # ... procesar frame
        # Auto-release al salir del 'with'
    """
    
    _instance: Optional['CameraManager'] = None
    _lock = threading.Lock()  # Lock para crear el singleton
    
    def __new__(cls):
        """Implementación Singleton thread-safe (Double-checked locking)"""
        if cls._instance is None:
            with cls._lock:
                # Double-check para evitar race condition
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialize()
                    cls._instance = instance
        return cls._instance
    
    def _initialize(self):
        """Inicializa las variables de instancia (solo se ejecuta una vez)"""
        self._camera: Optional[cv2.VideoCapture] = None
        self._camera_lock = threading.Lock()  # Lock para operaciones de cámara
        self._in_use = False
        self._current_user: Optional[str] = None
        self._camera_index = 0  # Cámara por defecto
        
        logger.info("CameraManager inicializado (Singleton)")
    
    @contextmanager
    def acquire_camera(
        self, 
        user_id: str, 
        camera_index: int = 0,
        width: int = 1280,
        height: int = 720
    ) -> Generator[cv2.VideoCapture, None, None]:
        """
        Context manager para adquirir acceso exclusivo a la cámara
        
        Args:
            user_id: Identificador del usuario/sesión
            camera_index: Índice de la cámara (0 = predeterminada)
            width: Ancho de resolución deseado
            height: Alto de resolución deseado
        
        Yields:
            cv2.VideoCapture: Objeto de captura de video configurado
        
        Raises:
            RuntimeError: Si la cámara ya está en uso o no se puede abrir
        
        Example:
            with camera_manager.acquire_camera('user123') as cap:
                ret, frame = cap.read()
                if ret:
                    # Procesar frame...
        """
        with self._camera_lock:
            # Verificar si ya está en uso
            if self._in_use:
                error_msg = (
                    f"Cámara en uso por '{self._current_user}'. "
                    f"Cierra la sesión anterior primero."
                )
                logger.warning(f"Intento de acceso concurrente por '{user_id}': {error_msg}")
                raise RuntimeError(error_msg)
            
            # Intentar abrir la cámara
            self._camera = cv2.VideoCapture(camera_index)
            
            if not self._camera.isOpened():
                self._camera = None
                error_msg = f"No se pudo abrir la cámara (índice {camera_index})"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Configurar resolución
            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # Verificar resolución real obtenida
            actual_width = int(self._camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self._camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self._camera.get(cv2.CAP_PROP_FPS))
            
            # Marcar como en uso
            self._in_use = True
            self._current_user = user_id
            self._camera_index = camera_index
            
            logger.info(
                f"Cámara adquirida por '{user_id}' | "
                f"Resolución: {actual_width}x{actual_height} @ {actual_fps}fps"
            )
        
        try:
            # Yield del objeto de cámara (sale del lock para permitir uso)
            yield self._camera
            
        except GeneratorExit:
            # Usuario cerró el navegador/tab sin hacer cleanup
            logger.warning(f"GeneratorExit detectado - Usuario '{user_id}' cerró stream abruptamente")
            
        except Exception as e:
            # Cualquier error durante el uso
            logger.error(f"Error durante uso de cámara por '{user_id}': {e}", exc_info=True)
            
        finally:
            # SIEMPRE liberar recursos (incluso si hay error)
            with self._camera_lock:
                if self._camera is not None:
                    self._camera.release()
                    self._camera = None
                    logger.info(f"Cámara liberada por '{user_id}'")
                
                self._in_use = False
                self._current_user = None
    
    def is_available(self) -> bool:
        """
        Verifica si la cámara está disponible para uso
        
        Returns:
            bool: True si está disponible, False si está en uso
        """
        with self._camera_lock:
            return not self._in_use
    
    def get_current_user(self) -> Optional[str]:
        """
        Obtiene el ID del usuario que está usando la cámara actualmente
        
        Returns:
            str | None: ID del usuario actual o None si no está en uso
        """
        with self._camera_lock:
            return self._current_user
    
    def force_release(self) -> bool:
        """
        Libera la cámara forzadamente (solo usar en emergencias)
        
        ADVERTENCIA: Usar con precaución. Puede dejar al usuario anterior
        en estado inconsistente.
        
        Returns:
            bool: True si se liberó exitosamente, False si ya estaba libre
        """
        with self._camera_lock:
            if not self._in_use:
                logger.info("force_release(): Cámara ya estaba libre")
                return False
            
            previous_user = self._current_user
            
            if self._camera is not None:
                self._camera.release()
                self._camera = None
            
            self._in_use = False
            self._current_user = None
            
            logger.warning(
                f"FORCE RELEASE ejecutado - Cámara liberada forzadamente "
                f"(usuario anterior: '{previous_user}')"
            )
            return True
    
    def get_status(self) -> dict:
        """
        Obtiene el estado actual del gestor de cámara
        
        Returns:
            dict: Diccionario con información de estado
        """
        with self._camera_lock:
            return {
                'available': not self._in_use,
                'in_use': self._in_use,
                'current_user': self._current_user,
                'camera_index': self._camera_index if self._in_use else None,
                'camera_open': self._camera is not None and self._camera.isOpened() if self._camera else False
            }
    
    def __repr__(self) -> str:
        """Representación en string del estado del manager"""
        status = self.get_status()
        if status['in_use']:
            return f"<CameraManager: IN USE by '{status['current_user']}'>"
        else:
            return "<CameraManager: AVAILABLE>"


# Instancia global singleton (crear una sola vez al importar el módulo)
camera_manager = CameraManager()


# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def check_camera_availability() -> tuple[bool, str]:
    """
    Verifica si la cámara está disponible antes de intentar usarla
    
    Returns:
        tuple: (disponible: bool, mensaje: str)
    
    Example:
        available, message = check_camera_availability()
        if not available:
            flash(message, 'error')
            return redirect(...)
    """
    if not camera_manager.is_available():
        current_user = camera_manager.get_current_user()
        return False, f"La cámara está en uso por '{current_user}'. Cierra esa sesión primero."
    return True, "Cámara disponible"


def get_camera_info() -> dict:
    """
    Obtiene información técnica de la cámara (requiere que esté libre)
    
    Returns:
        dict: Información de la cámara o error
    """
    if not camera_manager.is_available():
        return {
            'error': 'Camera in use',
            'current_user': camera_manager.get_current_user()
        }
    
    try:
        # Abrir temporalmente para obtener info
        test_cap = cv2.VideoCapture(0)
        
        if not test_cap.isOpened():
            return {'error': 'Cannot open camera'}
        
        info = {
            'width': int(test_cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(test_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': int(test_cap.get(cv2.CAP_PROP_FPS)),
            'backend': test_cap.getBackendName(),
            'available': True
        }
        
        test_cap.release()
        return info
        
    except Exception as e:
        return {'error': str(e)}
