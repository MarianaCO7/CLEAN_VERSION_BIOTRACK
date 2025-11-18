"""
💪 SHOULDER PROFILE ANALYZER - Análisis de Flexión/Extensión de Hombro
========================================================================
Analizador para vista de PERFIL (medición de flexión/extensión del hombro)

ADAPTADO PARA FLASK:
- Sin cv2.imshow() ni cv2.waitKey()
- Solo procesa frames y retorna frame anotado
- Gestión de estado interno (ángulos, ROM máximo)
- API pública para obtener datos actuales

Autor: BIOTRACK Team
Fecha: 2025-11-14
Basado en: tests/test_shoulder_profile.py
"""

import cv2
import numpy as np
import mediapipe as mp
import time
from collections import deque
from typing import Dict, Any, Tuple, Optional

# Inicializar MediaPipe Pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles


class ShoulderProfileAnalyzer:
    """
    Analizador de hombro en vista de PERFIL
    
    Mide:
    - Flexión (brazo hacia adelante/arriba)
    - Extensión (brazo hacia atrás)
    - ROM máximo alcanzado
    
    Uso en Flask:
        analyzer = ShoulderProfileAnalyzer()
        
        # En loop de video stream:
        processed_frame = analyzer.process_frame(frame)
        current_data = analyzer.get_current_data()
    """
    
    def __init__(
        self, 
        processing_width: int = 640, 
        processing_height: int = 480,
        show_skeleton: bool = False
    ):
        """
        Inicializa el analizador para vista de PERFIL
        
        Args:
            processing_width: Ancho para procesamiento de MediaPipe
            processing_height: Alto para procesamiento de MediaPipe
            show_skeleton: Si mostrar el skeleton completo de MediaPipe
        """
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=0,  # Lite model (2x más rápido, error adicional: ±0.8°)
            enable_segmentation=False,  # Desactivar segmentación para mayor velocidad
            smooth_landmarks=True  # Suavizado de landmarks para mejor estabilidad
        )
        
        # Resolución de procesamiento
        self.processing_width = processing_width
        self.processing_height = processing_height
        
        # Variables para tracking de ángulos
        self.current_angle = 0.0
        self.max_angle = 0.0
        self.side = "Detectando..."
        self.orientation = "Detectando..."
        self.confidence = 0.0
        self.frame_count = 0
        
        # Configuración de visualización
        self.show_skeleton = show_skeleton
        
        # Métricas de rendimiento
        self.fps_history = deque(maxlen=30)
        self.processing_times = deque(maxlen=30)
        self.last_time = time.time()
        
        # Caché de colores
        self.color_cache = {
            'white': (255, 255, 255),
            'yellow': (0, 255, 255),
            'orange': (0, 165, 255),
            'magenta': (255, 0, 255),
            'green': (0, 255, 0),
            'cyan': (255, 255, 0),
            'blue': (255, 0, 0),
            'red': (0, 0, 255),
            'gray': (50, 50, 50),
            'light_gray': (200, 200, 200)
        }
        
        # Estado de postura
        self.posture_valid = False
        self.landmarks_detected = False
    
    def calculate_extension_angle(
        self, 
        shoulder: Tuple[int, int], 
        elbow: Tuple[int, int], 
        side: str
    ) -> float:
        """
        Calcula el ángulo de flexión/extensión con eje vertical fijo
        
        Sistema goniómetro estándar:
        - Brazo FIJO: Eje vertical absoluto (0, 1)
        - Brazo MÓVIL: Línea del brazo (hombro → codo)
        - 0° = Brazo hacia abajo
        - +ángulo = Flexión (adelante)
        - -ángulo = Extensión (atrás)
        
        Args:
            shoulder: Coordenadas (x, y) del hombro
            elbow: Coordenadas (x, y) del codo
            side: 'left' o 'right'
        
        Returns:
            float: Ángulo en grados (positivo=flexión, negativo=extensión)
        """
        vertical_down_vector = np.array([0, 1])
        arm_vector = np.array([elbow[0] - shoulder[0], elbow[1] - shoulder[1]])
        
        arm_norm = np.linalg.norm(arm_vector)
        if arm_norm == 0:
            return 0.0
        
        arm_vector_normalized = arm_vector / arm_norm
        
        # Calcular ángulo
        dot_product = np.dot(vertical_down_vector, arm_vector_normalized)
        dot_product = np.clip(dot_product, -1.0, 1.0)
        angle_magnitude = np.degrees(np.arccos(dot_product))
        
        # Determinar dirección (producto cruz simplificado)
        cross_product = -arm_vector[0]
        
        if side == 'left':
            angle = angle_magnitude if cross_product > 0 else -angle_magnitude
        else:
            angle = angle_magnitude if cross_product < 0 else -angle_magnitude
        
        return float(angle)
    
    def detect_side(self, landmarks) -> Tuple[str, float, str]:
        """
        Detecta qué lado del cuerpo está visible (vista de perfil)
        
        Args:
            landmarks: Lista de landmarks de MediaPipe
        
        Returns:
            tuple: (lado, confianza, orientación)
                - lado: 'left' o 'right'
                - confianza: float (0-1)
                - orientación: str descripción de la orientación
        """
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        nose = landmarks[mp_pose.PoseLandmark.NOSE]
        
        # Método: Solo visibilidad
        left_visibility = left_shoulder.visibility
        right_visibility = right_shoulder.visibility
        
        shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2
        
        if left_visibility > right_visibility:
            side = 'left'
            confidence = left_visibility
            orientation = "mirando izquierda" if nose.x < shoulder_center_x else "mirando derecha"
        else:
            side = 'right'
            confidence = right_visibility
            orientation = "mirando derecha" if nose.x > shoulder_center_x else "mirando izquierda"
        
        return side, float(confidence), orientation
    
    def get_landmarks_2d(
        self, 
        landmark, 
        frame_width: int, 
        frame_height: int
    ) -> Tuple[int, int]:
        """
        Convierte landmarks normalizados a coordenadas de píxeles
        
        Args:
            landmark: Landmark de MediaPipe (normalizado 0-1)
            frame_width: Ancho del frame en píxeles
            frame_height: Alto del frame en píxeles
        
        Returns:
            tuple: (x, y) en coordenadas de píxeles
        """
        return (
            int(landmark.x * frame_width), 
            int(landmark.y * frame_height)
        )
    
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Procesa un frame y retorna el frame anotado
        
        MÉTODO PRINCIPAL - Llamar en cada frame del video stream
        
        Args:
            frame: Frame de OpenCV (BGR numpy array)
        
        Returns:
            np.ndarray: Frame procesado con anotaciones visuales
        """
        start_time = time.time()
        self.frame_count += 1
        
        # Guardar dimensiones originales
        original_h, original_w = frame.shape[:2]
        
        # Reducir resolución para procesamiento
        small_frame = cv2.resize(
            frame, 
            (self.processing_width, self.processing_height), 
            interpolation=cv2.INTER_LINEAR
        )
        
        # Convertir a RGB
        image_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False
        
        # Procesar con MediaPipe
        results = self.pose.process(image_rgb)
        
        # Trabajar con resolución original para visualización
        image_rgb.flags.writeable = True
        image = frame.copy()
        
        if results.pose_landmarks:
            self.landmarks_detected = True
            h, w = image.shape[:2]
            landmarks = results.pose_landmarks.landmark
            
            # Detectar lado visible
            side, confidence, orientation = self.detect_side(landmarks)
            self.side = "HOMBRO IZQUIERDO" if side == 'left' else "HOMBRO DERECHO"
            self.orientation = orientation
            self.confidence = confidence
            
            # Dibujar skeleton solo si está habilitado
            if self.show_skeleton:
                mp_drawing.draw_landmarks(
                    image,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
                )
            
            # Procesar vista de perfil
            self._process_profile_view(image, landmarks, w, h, side, orientation, confidence)
        else:
            self.landmarks_detected = False
            self.posture_valid = False
            cv2.putText(
                image, 
                "No se detecta persona", 
                (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 
                1, 
                self.color_cache['red'], 
                2, 
                cv2.LINE_4
            )
        
        # Calcular métricas de rendimiento
        processing_time = (time.time() - start_time) * 1000
        self.processing_times.append(processing_time)
        
        current_time = time.time()
        fps = 1.0 / (current_time - self.last_time) if (current_time - self.last_time) > 0 else 0
        self.fps_history.append(fps)
        self.last_time = current_time
        
        # Mostrar métricas (opcional, puede deshabilitarse)
        self._draw_performance_metrics(image, fps, processing_time)
        
        return image
    
    def _process_profile_view(
        self, 
        image: np.ndarray, 
        landmarks, 
        w: int, 
        h: int, 
        side: str, 
        orientation: str, 
        confidence: float
    ):
        """Procesa vista de perfil - Análisis de extensión/flexión"""
        # Seleccionar landmarks según el lado detectado
        if side == 'left':
            shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
            hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
            elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
            wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
        else:
            shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
            hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
            elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
            wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
        
        # Obtener coordenadas 2D
        shoulder_2d = self.get_landmarks_2d(shoulder, w, h)
        hip_2d = self.get_landmarks_2d(hip, w, h)
        elbow_2d = self.get_landmarks_2d(elbow, w, h)
        wrist_2d = self.get_landmarks_2d(wrist, w, h)
        
        # Calcular ángulo de extensión/flexión
        angle = self.calculate_extension_angle(shoulder_2d, elbow_2d, side)
        
        # Actualizar estadísticas
        self.current_angle = angle
        
        abs_angle = abs(angle)
        if abs_angle > self.max_angle:
            self.max_angle = abs_angle
        
        # Validar postura (simplificado - mejorar según necesidades)
        self.posture_valid = confidence > 0.6 and abs_angle < 200  # Ángulo razonable
        
        # Dibujar puntos clave
        cv2.circle(image, shoulder_2d, 8, self.color_cache['yellow'], -1, cv2.LINE_4)
        cv2.circle(image, hip_2d, 8, self.color_cache['magenta'], -1, cv2.LINE_4)
        cv2.circle(image, elbow_2d, 8, self.color_cache['cyan'], -1, cv2.LINE_4)
        
        # Línea de referencia vertical fija
        vertical_length = 150
        vertical_start = (shoulder_2d[0], shoulder_2d[1] - vertical_length)
        vertical_end = (shoulder_2d[0], shoulder_2d[1] + vertical_length)
        cv2.line(image, vertical_start, vertical_end, self.color_cache['green'], 3, cv2.LINE_4)
        
        # Línea del brazo
        cv2.line(image, shoulder_2d, elbow_2d, self.color_cache['blue'], 3, cv2.LINE_4)
        
        # Antebrazo
        cv2.line(image, elbow_2d, wrist_2d, self.color_cache['blue'], 2, cv2.LINE_4)
        
        # Mostrar ángulo
        angle_text = f"{abs(angle):.1f}°"
        direction_text = "FLEX" if angle > 0 else "EXT" if angle < 0 else ""
        cv2.putText(
            image, 
            angle_text, 
            (shoulder_2d[0] - 40, shoulder_2d[1] - 20),
            cv2.FONT_HERSHEY_SIMPLEX, 
            1.2, 
            self.color_cache['yellow'], 
            3, 
            cv2.LINE_4
        )
        if direction_text:
            direction_color = self.color_cache['green'] if angle > 0 else self.color_cache['orange']
            cv2.putText(
                image, 
                direction_text, 
                (shoulder_2d[0] - 30, shoulder_2d[1] + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.5, 
                direction_color, 
                2, 
                cv2.LINE_4
            )
        
        # Panel de información
        self._draw_info_panel(image, orientation, confidence, w, h)
    
    def _draw_info_panel(
        self, 
        image: np.ndarray, 
        orientation: str, 
        confidence: float, 
        w: int, 
        h: int
    ):
        """Dibuja el panel de información en la imagen"""
        # Panel superior con información
        panel_height = 180
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (w, panel_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
        
        # Título
        cv2.putText(
            image, 
            "FLEXION/EXTENSION DE HOMBRO (PERFIL)", 
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.7, 
            self.color_cache['white'], 
            2, 
            cv2.LINE_4
        )
        
        # Lado detectado
        color_side = self.color_cache['green'] if confidence > 0.7 else self.color_cache['orange']
        cv2.putText(
            image, 
            f"Lado: {self.side}", 
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            color_side, 
            2, 
            cv2.LINE_4
        )
        
        # Orientación
        cv2.putText(
            image, 
            f"Orientacion: {orientation}", 
            (20, 100),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.5, 
            self.color_cache['white'], 
            1, 
            cv2.LINE_4
        )
        
        # Ángulo actual
        angle_color = self._get_angle_color(self.current_angle)
        direction_text = "FLEX" if self.current_angle > 0 else "EXT" if self.current_angle < 0 else ""
        cv2.putText(
            image, 
            f"Angulo: {abs(self.current_angle):.1f}deg {direction_text}", 
            (20, 130),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            angle_color, 
            2, 
            cv2.LINE_4
        )
        
        # ROM Máximo
        cv2.putText(
            image, 
            f"ROM Max: {self.max_angle:.1f}deg", 
            (20, 160),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            self.color_cache['green'], 
            2, 
            cv2.LINE_4
        )
    
    def _draw_performance_metrics(
        self, 
        image: np.ndarray, 
        current_fps: float, 
        current_processing_time: float
    ):
        """Dibuja métricas de rendimiento en pantalla"""
        h, w = image.shape[:2]
        
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        
        panel_x = w - 200
        panel_y = 10
        
        # Fondo semitransparente
        overlay = image.copy()
        cv2.rectangle(
            overlay, 
            (panel_x - 10, panel_y), 
            (w - 10, panel_y + 80), 
            self.color_cache['gray'], 
            -1
        )
        cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)
        
        # Métricas
        cv2.putText(
            image, 
            f"FPS: {current_fps:.1f}", 
            (panel_x, panel_y + 25),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.5, 
            self.color_cache['green'], 
            1, 
            cv2.LINE_4
        )
        
        cv2.putText(
            image, 
            f"Latencia: {current_processing_time:.1f}ms", 
            (panel_x, panel_y + 50),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.4, 
            self.color_cache['yellow'], 
            1, 
            cv2.LINE_4
        )
    
    def _get_angle_color(self, angle: float) -> Tuple[int, int, int]:
        """Retorna color según el ángulo"""
        abs_angle = abs(angle)
        
        if abs_angle < 15:
            return self.color_cache['white']
        elif abs_angle < 45:
            return self.color_cache['yellow']
        elif abs_angle < 90:
            return self.color_cache['orange']
        elif abs_angle < 135:
            return self.color_cache['magenta']
        else:
            return self.color_cache['green']
    
    def get_current_data(self) -> Dict[str, Any]:
        """
        Obtiene los datos actuales del análisis
        
        Returns:
            dict: Diccionario con datos actuales:
                - angle: Ángulo actual (float)
                - max_rom: ROM máximo alcanzado (float)
                - side: Lado detectado (str)
                - orientation: Orientación (str)
                - confidence: Confianza de detección (float)
                - posture_valid: Si la postura es válida (bool)
                - landmarks_detected: Si se detectaron landmarks (bool)
                - fps: FPS actual (float)
        """
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        
        return {
            'angle': round(self.current_angle, 2),
            'max_rom': round(self.max_angle, 2),
            'side': self.side,
            'orientation': self.orientation,
            'confidence': round(self.confidence, 2),
            'posture_valid': self.posture_valid,
            'landmarks_detected': self.landmarks_detected,
            'fps': round(avg_fps, 1),
            'frame_count': self.frame_count
        }
    
    def reset(self):
        """
        Reinicia todas las estadísticas (ROM, ángulos, etc.)
        
        Útil para iniciar una nueva sesión de medición sin recrear el analyzer
        """
        self.max_angle = 0.0
        self.current_angle = 0.0
        self.fps_history.clear()
        self.processing_times.clear()
        self.frame_count = 0
        self.posture_valid = False
        self.landmarks_detected = False
    
    def cleanup(self):
        """
        Libera recursos de MediaPipe
        
        Llamar cuando ya no se necesite el analyzer
        """
        if self.pose:
            self.pose.close()
            self.pose = None
