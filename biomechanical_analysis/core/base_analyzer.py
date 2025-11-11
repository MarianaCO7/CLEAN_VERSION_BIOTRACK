import cv2
import mediapipe as mp
import numpy as np
import math
from abc import ABC, abstractmethod
from collections import deque
from PIL import Image, ImageDraw, ImageFont
from .mediapipe_config import MediaPipeConfig

class BaseJointAnalyzer(ABC):
    """
    🎯 CLASE BASE para análisis de articulaciones
    📋 MIGRADA EXACTAMENTE desde test_elbow_upper_body.py
    ✅ CONSERVA todas las funciones que funcionan perfecto
    """
    
    def __init__(self, joint_name):
        self.joint_name = joint_name
        
        # � CONFIGURACIÓN OPTIMIZADA DE MEDIAPIPE
        self.mp_pose = mp.solutions.pose
        
        # Usar configuración automática según entorno (Railway vs Local)
        self.pose = MediaPipeConfig.create_pose_detector()
        self.mp_draw = mp.solutions.drawing_utils
        
        # Obtener configuraciones optimizadas
        self.config = MediaPipeConfig.get_optimized_settings()
        
        print(f"✅ MediaPipe configurado para {joint_name}")
        print(f"🎯 Modelo complexity: {self.config['model_complexity']}")
        print(f"🎯 Detection confidence: {self.config['min_detection_confidence']}")
        
        # 🔄 TU SISTEMA DE FILTROS (PERFECTO - NO CAMBIAR)
        self.angle_filters = {}
    
    # ✅ TU FUNCIÓN EXACTA - MATEMÁTICA CORRECTA
    def calculate_angle_biomechanical(self, point1, point2, point3):
        """
        Cálculo biomecánico correcto
        MIGRADO EXACTO desde test_elbow_upper_body.py
        """
        vector1 = np.array(point1) - np.array(point2)
        vector2 = np.array(point3) - np.array(point2)
        
        dot_product = np.dot(vector1, vector2)
        magnitude1 = np.linalg.norm(vector1)
        magnitude2 = np.linalg.norm(vector2)
        
        if magnitude1 * magnitude2 == 0:
            return 0
        
        cos_angle = dot_product / (magnitude1 * magnitude2)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle = np.arccos(cos_angle)
        return np.degrees(angle)
    
    # ✅ TU FILTRO EXACTO - FUNCIONA PERFECTO
    def apply_temporal_filter(self, new_angle, filter_name):
        """
        Filtro temporal para suavizar ángulos
        MIGRADO EXACTO desde test_elbow_upper_body.py
        """
        if filter_name not in self.angle_filters:
            self.angle_filters[filter_name] = deque(maxlen=5)
        
        filter_queue = self.angle_filters[filter_name]
        filter_queue.append(new_angle)
        
        if len(filter_queue) < 3:
            return new_angle  # Devuelve original si no hay suficientes datos
        
        # Filtro mediana simple - elimina valores extremos
        return np.median(list(filter_queue))
    
    # ✅ TU FUNCIÓN PILLOW EXACTA - SÍMBOLOS UNICODE PERFECTOS
    def add_text_with_pillow(self, frame, text, position, font_size=20, color=(255, 255, 255)):
        """🎨 Agregar texto con PIL (símbolos Unicode correctos)"""
        
        try:
            from PIL import Image, ImageDraw, ImageFont
            import numpy as np
            
            # Convertir a PIL
            pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_image)
            
            # Fuente
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            # Dibujar texto
            draw.text(position, text, font=font, fill=color)
            
            # Convertir de vuelta
            return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            # Fallback a OpenCV si PIL falla
            cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 
                       font_size/30, color, 2)
            return frame
    
    # ✅ TU FUNCIÓN DE ARCOS EXACTA - VISUALIZACIÓN PERFECTA
    def draw_angle_arc_advanced(self, img, center, point1, point2, angle, radius=30, color=(255, 255, 0)):
        """
        Dibuja arco con texto mejorado usando Pillow
        MIGRADO EXACTO desde test_elbow_upper_body.py
        """
        vector1 = np.array(point1) - np.array(center)
        vector2 = np.array(point2) - np.array(center)
        
        angle1 = math.atan2(vector1[1], vector1[0])
        angle2 = math.atan2(vector2[1], vector2[0])
        
        if angle2 < angle1:
            angle1, angle2 = angle2, angle1
        
        cv2.ellipse(img, tuple(map(int, center)), (radius, radius), 0, 
                   math.degrees(angle1), math.degrees(angle2), color, 2)
        
        text_pos = (int(center[0] + radius + 10), int(center[1] - 10))
        
        # 🔧 FIX: Si add_text_with_pillow falla, usar cv2.putText como fallback
        try:
            result = self.add_text_with_pillow(img, f"{angle:.0f}°", text_pos, font_size=16)
            if result is not None:
                img = result
            else:
                # Fallback: OpenCV nativo
                cv2.putText(img, f"{int(angle)}", text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        except Exception as e:
            # Fallback seguro
            cv2.putText(img, f"{int(angle)}", text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return img
    
    # ✅ TU VALIDACIÓN EXACTA - ROBUSTA
    def check_required_points_visible(self, landmarks, required_points=None):
        """
        Verifica que los puntos necesarios estén visibles
        MIGRADO EXACTO desde test_elbow_upper_body.py
        """
        if required_points is None:
            required_points = self.get_required_landmarks()
        
        for point_idx in required_points:
            if landmarks[point_idx].visibility < 0.3:
                return False
        return True
    
    # ⏰ MÉTODO PARA GENERAR TIMESTAMP
    def get_timestamp(self):
        """⏰ Genera timestamp para el análisis"""
        import time
        if not hasattr(self, '_start_time'):
            self._start_time = time.time()
        return time.time() - self._start_time
    
    # 🎯 MÉTODOS ABSTRACTOS (cada articulación los implementa)
    @abstractmethod
    def get_required_landmarks(self):
        """Retorna landmarks necesarios para esta articulación"""
        pass
    
    @abstractmethod
    def calculate_joint_angles(self, landmarks, frame_dimensions):
        """Calcula ángulos específicos de la articulación"""
        pass
    
    @abstractmethod
    def draw_joint_visualization(self, frame, landmarks, angles):
        """Dibuja visualización específica de la articulación"""
        pass
    
    def detect_orientation(self, landmarks):
        """🧭 DETECTAR ORIENTACIÓN usando AdaptiveOrientationDetector"""
        try:
            from core.orientation_detector import AdaptiveOrientationDetector
            detector = AdaptiveOrientationDetector()
            return detector.detect_orientation_simple(landmarks)
        except Exception as e:
            # Fallback simple si hay error
            return {
                "orientation": "FRONTAL", 
                "confidence": 0.5, 
                "primary_ratio": 2.0, 
                "analysis_type": "FALLBACK",
                "error": str(e)
            }