"""
💪 SHOULDER FRONTAL ANALYZER - Análisis de Abducción Bilateral de Hombros
===========================================================================
Analizador para vista FRONTAL (medición de abducción simultánea de ambos hombros)

ADAPTADO PARA FLASK:
- Sin cv2.imshow() ni cv2.waitKey()
- Solo procesa frames y retorna frame anotado
- Gestión de estado interno (ángulos bilaterales, ROM máximo)
- API pública para obtener datos actuales

Autor: BIOTRACK Team
Fecha: 2025-11-14
Basado en: tests/test_shoulder_frontal.py
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


class ShoulderFrontalAnalyzer:
    """
    Analizador de hombros en vista FRONTAL
    
    Mide:
    - Abducción bilateral (ambos brazos simultáneamente)
    - Simetría entre ambos lados
    - ROM máximo alcanzado para cada lado
    
    Uso en Flask:
        analyzer = ShoulderFrontalAnalyzer()
        
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
        Inicializa el analizador para vista FRONTAL
        
        Args:
            processing_width: Ancho para procesamiento de MediaPipe
            processing_height: Alto para procesamiento de MediaPipe
            show_skeleton: Si mostrar el skeleton completo de MediaPipe
        """
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1  # CPU mode
        )
        
        # Resolución de procesamiento
        self.processing_width = processing_width
        self.processing_height = processing_height
        
        # Variables para tracking de ángulos (bilateral)
        self.left_angle = 0.0
        self.right_angle = 0.0
        self.left_max_rom = 0.0
        self.right_max_rom = 0.0
        self.asymmetry = 0.0  # Diferencia entre ambos lados
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
            'light_gray': (200, 200, 200),
            'purple': (255, 0, 127)
        }
        
        # Estado de postura
        self.posture_valid = False
        self.landmarks_detected = False
        self.orientation_frontal = False
    
    def calculate_abduction_angle(
        self, 
        shoulder: Tuple[int, int], 
        hip: Tuple[int, int],
        elbow: Tuple[int, int]
    ) -> float:
        """
        Calcula el ángulo de abducción con eje vertical fijo
        
        Sistema goniómetro estándar:
        - Brazo FIJO: Línea vertical (hombro → cadera)
        - Brazo MÓVIL: Línea del brazo (hombro → codo)
        - 0° = Brazo pegado al cuerpo
        - 90° = Brazo horizontal
        - 180° = Brazo arriba (sobre la cabeza)
        
        Args:
            shoulder: Coordenadas (x, y) del hombro
            hip: Coordenadas (x, y) de la cadera
            elbow: Coordenadas (x, y) del codo
        
        Returns:
            float: Ángulo de abducción en grados (0-180)
        """
        # Vector vertical de referencia (hombro → cadera)
        vertical_vector = np.array([hip[0] - shoulder[0], hip[1] - shoulder[1]])
        
        # Vector del brazo (hombro → codo)
        arm_vector = np.array([elbow[0] - shoulder[0], elbow[1] - shoulder[1]])
        
        # Normalizar vectores
        vertical_norm = np.linalg.norm(vertical_vector)
        arm_norm = np.linalg.norm(arm_vector)
        
        if vertical_norm == 0 or arm_norm == 0:
            return 0.0
        
        vertical_normalized = vertical_vector / vertical_norm
        arm_normalized = arm_vector / arm_norm
        
        # Calcular ángulo usando producto punto
        dot_product = np.dot(vertical_normalized, arm_normalized)
        dot_product = np.clip(dot_product, -1.0, 1.0)
        angle = np.degrees(np.arccos(dot_product))
        
        return float(angle)
    
    def detect_frontal_orientation(self, landmarks) -> Tuple[bool, float]:
        """
        Detecta si la persona está en vista frontal
        
        Args:
            landmarks: Lista de landmarks de MediaPipe
        
        Returns:
            tuple: (es_frontal: bool, confianza: float)
        """
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        
        # En vista frontal, ambos hombros tienen visibilidad similar y alta
        left_vis = left_shoulder.visibility
        right_vis = right_shoulder.visibility
        
        avg_visibility = (left_vis + right_vis) / 2
        visibility_diff = abs(left_vis - right_vis)
        
        # Criterios para vista frontal:
        # 1. Ambos hombros visibles (avg > 0.6)
        # 2. Visibilidad similar entre ambos (diff < 0.2)
        is_frontal = avg_visibility > 0.6 and visibility_diff < 0.2
        confidence = avg_visibility
        
        return is_frontal, float(confidence)
    
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
            
            # Detectar orientación frontal
            is_frontal, confidence = self.detect_frontal_orientation(landmarks)
            self.orientation_frontal = is_frontal
            
            # Dibujar skeleton solo si está habilitado
            if self.show_skeleton:
                mp_drawing.draw_landmarks(
                    image,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
                )
            
            if is_frontal:
                # Procesar vista frontal (abducción bilateral)
                self._process_frontal_view(image, landmarks, w, h, confidence)
            else:
                # No es vista frontal
                self.posture_valid = False
                cv2.putText(
                    image, 
                    "Colocate de FRENTE a la camara", 
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    1, 
                    self.color_cache['orange'], 
                    2, 
                    cv2.LINE_4
                )
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
        
        # Mostrar métricas
        self._draw_performance_metrics(image, fps, processing_time)
        
        return image
    
    def _process_frontal_view(
        self, 
        image: np.ndarray, 
        landmarks, 
        w: int, 
        h: int, 
        confidence: float
    ):
        """Procesa vista frontal - Análisis de abducción bilateral"""
        # Obtener landmarks de ambos lados
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
        right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
        right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
        
        # Convertir a coordenadas 2D
        left_shoulder_2d = self.get_landmarks_2d(left_shoulder, w, h)
        right_shoulder_2d = self.get_landmarks_2d(right_shoulder, w, h)
        left_hip_2d = self.get_landmarks_2d(left_hip, w, h)
        right_hip_2d = self.get_landmarks_2d(right_hip, w, h)
        left_elbow_2d = self.get_landmarks_2d(left_elbow, w, h)
        right_elbow_2d = self.get_landmarks_2d(right_elbow, w, h)
        left_wrist_2d = self.get_landmarks_2d(left_wrist, w, h)
        right_wrist_2d = self.get_landmarks_2d(right_wrist, w, h)
        
        # Calcular ángulos de abducción para ambos lados
        left_angle = self.calculate_abduction_angle(
            left_shoulder_2d, left_hip_2d, left_elbow_2d
        )
        right_angle = self.calculate_abduction_angle(
            right_shoulder_2d, right_hip_2d, right_elbow_2d
        )
        
        # Actualizar estadísticas
        self.left_angle = left_angle
        self.right_angle = right_angle
        
        if left_angle > self.left_max_rom:
            self.left_max_rom = left_angle
        if right_angle > self.right_max_rom:
            self.right_max_rom = right_angle
        
        # Calcular asimetría
        self.asymmetry = abs(left_angle - right_angle)
        
        # Validar postura
        self.posture_valid = (
            confidence > 0.6 and 
            left_angle < 200 and 
            right_angle < 200 and
            self.asymmetry < 40  # Diferencia razonable
        )
        
        # Dibujar puntos clave (LADO IZQUIERDO en perspectiva del usuario)
        cv2.circle(image, left_shoulder_2d, 8, self.color_cache['cyan'], -1, cv2.LINE_4)
        cv2.circle(image, left_hip_2d, 8, self.color_cache['magenta'], -1, cv2.LINE_4)
        cv2.circle(image, left_elbow_2d, 8, self.color_cache['yellow'], -1, cv2.LINE_4)
        
        # Dibujar puntos clave (LADO DERECHO en perspectiva del usuario)
        cv2.circle(image, right_shoulder_2d, 8, self.color_cache['cyan'], -1, cv2.LINE_4)
        cv2.circle(image, right_hip_2d, 8, self.color_cache['magenta'], -1, cv2.LINE_4)
        cv2.circle(image, right_elbow_2d, 8, self.color_cache['yellow'], -1, cv2.LINE_4)
        
        # Líneas de referencia vertical (IZQUIERDA)
        cv2.line(image, left_shoulder_2d, left_hip_2d, self.color_cache['green'], 2, cv2.LINE_4)
        
        # Líneas de referencia vertical (DERECHA)
        cv2.line(image, right_shoulder_2d, right_hip_2d, self.color_cache['green'], 2, cv2.LINE_4)
        
        # Líneas del brazo (IZQUIERDA)
        cv2.line(image, left_shoulder_2d, left_elbow_2d, self.color_cache['blue'], 3, cv2.LINE_4)
        cv2.line(image, left_elbow_2d, left_wrist_2d, self.color_cache['blue'], 2, cv2.LINE_4)
        
        # Líneas del brazo (DERECHA)
        cv2.line(image, right_shoulder_2d, right_elbow_2d, self.color_cache['purple'], 3, cv2.LINE_4)
        cv2.line(image, right_elbow_2d, right_wrist_2d, self.color_cache['purple'], 2, cv2.LINE_4)
        
        # Mostrar ángulos en cada hombro
        cv2.putText(
            image, 
            f"{left_angle:.1f}°", 
            (left_shoulder_2d[0] - 60, left_shoulder_2d[1] - 20),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.8, 
            self.color_cache['cyan'], 
            2, 
            cv2.LINE_4
        )
        
        cv2.putText(
            image, 
            f"{right_angle:.1f}°", 
            (right_shoulder_2d[0] + 20, right_shoulder_2d[1] - 20),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.8, 
            self.color_cache['purple'], 
            2, 
            cv2.LINE_4
        )
        
        # Panel de información
        self._draw_info_panel(image, confidence, w, h)
        
        # Barras de progreso para cada lado
        self._draw_rom_bars(image, w, h)
    
    def _draw_info_panel(
        self, 
        image: np.ndarray, 
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
            "ABDUCCION BILATERAL DE HOMBROS (FRONTAL)", 
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.7, 
            self.color_cache['white'], 
            2, 
            cv2.LINE_4
        )
        
        # Ángulos actuales
        cv2.putText(
            image, 
            f"Izquierdo: {self.left_angle:.1f}deg | Derecho: {self.right_angle:.1f}deg", 
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            self.color_cache['cyan'], 
            2, 
            cv2.LINE_4
        )
        
        # ROM máximo de cada lado
        cv2.putText(
            image, 
            f"ROM Max: Izq {self.left_max_rom:.1f}deg | Der {self.right_max_rom:.1f}deg", 
            (20, 100),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            self.color_cache['green'], 
            2, 
            cv2.LINE_4
        )
        
        # Asimetría
        asymmetry_color = self.color_cache['green'] if self.asymmetry < 15 else self.color_cache['orange']
        cv2.putText(
            image, 
            f"Asimetria: {self.asymmetry:.1f}deg", 
            (20, 130),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            asymmetry_color, 
            2, 
            cv2.LINE_4
        )
        
        # Estado de postura
        posture_text = "Postura correcta" if self.posture_valid else "Ajusta postura"
        posture_color = self.color_cache['green'] if self.posture_valid else self.color_cache['orange']
        cv2.putText(
            image, 
            posture_text, 
            (20, 160),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            posture_color, 
            2, 
            cv2.LINE_4
        )
    
    def _draw_rom_bars(self, image: np.ndarray, w: int, h: int):
        """Dibuja barras de progreso verticales para ROM de cada lado"""
        bar_width = 40
        bar_max_height = 200
        bar_x_left = w - 120
        bar_x_right = w - 60
        bar_y_bottom = h - 50
        
        # Calcular alturas de barras (0-180° = 0-100%)
        left_bar_height = int((self.left_angle / 180) * bar_max_height)
        right_bar_height = int((self.right_angle / 180) * bar_max_height)
        
        # Fondo de las barras
        cv2.rectangle(
            image, 
            (bar_x_left, bar_y_bottom - bar_max_height), 
            (bar_x_left + bar_width, bar_y_bottom), 
            self.color_cache['gray'], 
            -1
        )
        cv2.rectangle(
            image, 
            (bar_x_right, bar_y_bottom - bar_max_height), 
            (bar_x_right + bar_width, bar_y_bottom), 
            self.color_cache['gray'], 
            -1
        )
        
        # Barras de progreso
        cv2.rectangle(
            image, 
            (bar_x_left, bar_y_bottom - left_bar_height), 
            (bar_x_left + bar_width, bar_y_bottom), 
            self.color_cache['cyan'], 
            -1
        )
        cv2.rectangle(
            image, 
            (bar_x_right, bar_y_bottom - right_bar_height), 
            (bar_x_right + bar_width, bar_y_bottom), 
            self.color_cache['purple'], 
            -1
        )
        
        # Etiquetas
        cv2.putText(
            image, 
            "IZQ", 
            (bar_x_left + 5, bar_y_bottom + 20),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.4, 
            self.color_cache['white'], 
            1, 
            cv2.LINE_4
        )
        cv2.putText(
            image, 
            "DER", 
            (bar_x_right + 5, bar_y_bottom + 20),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.4, 
            self.color_cache['white'], 
            1, 
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
        panel_y = h - 100
        
        # Fondo semitransparente
        overlay = image.copy()
        cv2.rectangle(
            overlay, 
            (panel_x - 10, panel_y), 
            (w - 10, h - 10), 
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
    
    def get_current_data(self) -> Dict[str, Any]:
        """
        Obtiene los datos actuales del análisis
        
        Returns:
            dict: Diccionario con datos actuales:
                - left_angle: Ángulo izquierdo actual (float)
                - right_angle: Ángulo derecho actual (float)
                - left_max_rom: ROM máximo izquierdo (float)
                - right_max_rom: ROM máximo derecho (float)
                - asymmetry: Asimetría entre lados (float)
                - posture_valid: Si la postura es válida (bool)
                - landmarks_detected: Si se detectaron landmarks (bool)
                - orientation_frontal: Si está en vista frontal (bool)
                - fps: FPS actual (float)
        """
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        
        return {
            'left_angle': round(self.left_angle, 2),
            'right_angle': round(self.right_angle, 2),
            'left_max_rom': round(self.left_max_rom, 2),
            'right_max_rom': round(self.right_max_rom, 2),
            'asymmetry': round(self.asymmetry, 2),
            'posture_valid': self.posture_valid,
            'landmarks_detected': self.landmarks_detected,
            'orientation_frontal': self.orientation_frontal,
            'fps': round(avg_fps, 1),
            'frame_count': self.frame_count
        }
    
    def reset(self):
        """
        Reinicia todas las estadísticas (ROM, ángulos, etc.)
        
        Útil para iniciar una nueva sesión de medición sin recrear el analyzer
        """
        self.left_angle = 0.0
        self.right_angle = 0.0
        self.left_max_rom = 0.0
        self.right_max_rom = 0.0
        self.asymmetry = 0.0
        self.fps_history.clear()
        self.processing_times.clear()
        self.frame_count = 0
        self.posture_valid = False
        self.landmarks_detected = False
        self.orientation_frontal = False
    
    def cleanup(self):
        """
        Libera recursos de MediaPipe
        
        Llamar cuando ya no se necesite el analyzer
        """
        if self.pose:
            self.pose.close()
            self.pose = None
