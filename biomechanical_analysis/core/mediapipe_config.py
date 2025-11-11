"""
🎯 CONFIGURACIÓN OPTIMIZADA DE MEDIAPIPE PARA RAILWAY
Detecta automáticamente el entorno y configura MediaPipe apropiadamente
"""
import os
import mediapipe as mp

class MediaPipeConfig:
    """Configurador inteligente de MediaPipe para diferentes entornos"""
    
    @staticmethod
    def is_railway_environment():
        """Detecta si estamos ejecutando en Railway"""
        return (
            os.getenv('RAILWAY_ENVIRONMENT') == 'production' or
            os.getenv('PORT') is not None or
            os.getenv('RAILWAY_PROJECT_ID') is not None or
            os.getenv('RAILWAY_SERVICE_ID') is not None
        )
    
    @staticmethod
    def create_pose_detector():
        """
        Crea un detector de pose optimizado según el entorno
        Railway = CPU only (sin GPU/OpenGL)
        Local = Configuración por defecto
        """
        is_railway = MediaPipeConfig.is_railway_environment()
        
        if is_railway:
            print("🌐 Entorno Railway detectado - Configurando MediaPipe para CPU")
            # Configuración CPU-only para Railway (sin GPU)
            # ⚠️ model_complexity=1 permite detección solo con piernas (sin requerir torso)
            pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=1,  # Balance: detecta piernas sin requerir hombros
                smooth_landmarks=True,
                min_detection_confidence=0.3,  # MUY BAJO: permite detección de perfil
                min_tracking_confidence=0.3,   # MUY BAJO: mantiene tracking en perfil
                enable_segmentation=False
            )
        else:
            print("💻 Entorno local detectado - Configuración MediaPipe estándar")
            # Configuración estándar para desarrollo local
            pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                smooth_landmarks=True,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.7,
                enable_segmentation=False
            )
        
        return pose
    
    @staticmethod
    def get_optimized_settings():
        """Obtiene configuraciones optimizadas según el entorno"""
        is_railway = MediaPipeConfig.is_railway_environment()
        
        if is_railway:
            return {
                'model_complexity': 1,  # Balance: piernas sin torso completo
                'min_detection_confidence': 0.3,  # MUY BAJO para perfil
                'min_tracking_confidence': 0.3,   # MUY BAJO para perfil
                'processing_fps': 5,  # Menor FPS en Railway
                'enable_gpu': False
            }
        else:
            return {
                'model_complexity': 1,
                'min_detection_confidence': 0.7,
                'min_tracking_confidence': 0.7,
                'processing_fps': 10,  # Mayor FPS local
                'enable_gpu': True
            }