"""
Script para análisis de ABDUCCIÓN/ADUCCIÓN bilateral de caderas (VISTA FRONTAL - PLANO FRONTAL)
Utiliza OpenCV y MediaPipe para detectar y calcular ángulos
Sistema de medición: Goniómetro clínico estándar con eje HORIZONTAL fijo

MÉTODO CLÍNICO CORRECTO (según imagen de referencia):
- VÉRTICE: Cadera (hip)
- BRAZO FIJO: Eje HORIZONTAL PURO (paralelo al borde de pantalla) que pasa por la CADERA
- BRAZO MÓVIL: Línea del muslo (CADERA → RODILLA)
- Medición interna: 90° = neutro (pierna perpendicular al eje horizontal)
- Conversión clínica: 0° = neutro, valores positivos = abducción

OPTIMIZACIONES IMPLEMENTADAS:
- Procesamiento en resolución reducida (640x480) con upscaling para display
- Dibujos OpenCV optimizados (LINE_4 en vez de LINE_AA)
- Caché de colores por rangos de ángulos
- Sistema de profiling de FPS y latencia
- Análisis de simetría bilateral
"""

import cv2
import mediapipe as mp
import numpy as np
import math
import time
from collections import deque

# Inicializar MediaPipe Pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

class HipFrontalAnalyzer:
    def __init__(self, processing_width=640, processing_height=480, selected_leg='both', exercise_type='abduccion'):
        """
        Inicializa el analizador para vista FRONTAL (Abducción/Aducción bilateral de caderas)
        
        Args:
            processing_width: Ancho para procesamiento de MediaPipe
            processing_height: Alto para procesamiento de MediaPipe
            selected_leg: Pierna a analizar ('left', 'right', 'both')
            exercise_type: Tipo de ejercicio ('abduccion' o 'aduccion')
        """
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1
        )
        
        # Resolución de procesamiento
        self.processing_width = processing_width
        self.processing_height = processing_height
        
        # Pierna seleccionada para análisis
        self.selected_leg = selected_leg
        
        # Tipo de ejercicio seleccionado
        self.exercise_type = exercise_type
        
        # Variables para tracking de ángulos (bilateral)
        self.left_hip_angle = 0
        self.right_hip_angle = 0
        self.max_left_abduction = 0
        self.max_right_abduction = 0
        self.frame_count = 0
        
        # Modo de visualización
        self.display_mode = "CLEAN"  # Opciones: "CLEAN", "FULL", "MINIMAL"
        
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
    
    def toggle_display_mode(self):
        """Alterna entre modos de visualización"""
        modes = ["CLEAN", "FULL", "MINIMAL"]
        current_index = modes.index(self.display_mode)
        next_index = (current_index + 1) % len(modes)
        self.display_mode = modes[next_index]
        
        mode_descriptions = {
            "CLEAN": "[*] LIMPIO - Solo lineas biomecanicas (Recomendado)",
            "FULL": "[*] COMPLETO - Con skeleton de MediaPipe",
            "MINIMAL": "[*] MINIMALISTA - Maximo rendimiento"
        }
        
        print(f"\n[*] Modo de visualizacion cambiado a: {mode_descriptions[self.display_mode]}")
        return self.display_mode
    
    def calculate_hip_abduction_angle(self, hip_left, hip_right, knee):
        """
        Calcula el ángulo de abducción/aducción de cadera con eje HORIZONTAL fijo (MÉTODO CLÍNICO CORRECTO)
        
        Sistema goniómetro clínico estándar (según imagen de referencia):
        - VÉRTICE: Cadera (hip)
        - Brazo FIJO: Eje HORIZONTAL PURO [1, 0] que pasa por la CADERA (paralelo a borde de pantalla)
        - Brazo MÓVIL: Línea del muslo (CADERA → RODILLA)
        
        Medición interna:
        - 90° = Pierna VERTICAL (posición neutra - perpendicular al eje horizontal)
        - >90° = ABDUCCIÓN (pierna separándose lateralmente)
        - <90° = ADUCCIÓN (pierna cruzándose - poco común en este ejercicio)
        
        Conversión a formato clínico (mostrado al usuario):
        - 0° = Neutro (90° interno)
        - 30° = Abducción moderada (120° interno)
        - 45° = Abducción alta (135° interno)
        
        Args:
            hip_left: Coordenadas [x, y] de la cadera IZQUIERDA
            hip_right: Coordenadas [x, y] de la cadera DERECHA
            knee: Coordenadas [x, y] de la rodilla
        
        Returns:
            float: Ángulo clínico en grados (0° = neutro, valores positivos = abducción)
        """
        # Determinar qué cadera estamos analizando (izquierda o derecha)
        # basándonos en cuál está más cerca de la rodilla
        dist_to_left = np.linalg.norm(np.array(knee) - np.array(hip_left))
        dist_to_right = np.linalg.norm(np.array(knee) - np.array(hip_right))
        
        if dist_to_left < dist_to_right:
            # Estamos analizando la pierna IZQUIERDA
            hip = hip_left
            # Para pierna izquierda, el eje horizontal apunta hacia la IZQUIERDA (X negativo)
            horizontal_ref = np.array([-1, 0])
        else:
            # Estamos analizando la pierna DERECHA
            hip = hip_right
            # Para pierna derecha, el eje horizontal apunta hacia la DERECHA (X positivo)
            horizontal_ref = np.array([1, 0])
        
        # Vector del muslo (CADERA → RODILLA) - brazo móvil del goniómetro
        thigh_vector = np.array([knee[0] - hip[0], knee[1] - hip[1]])
        
        # Normalizar vector del muslo
        thigh_norm = np.linalg.norm(thigh_vector)
        
        if thigh_norm == 0:
            return 0
        
        thigh_vector_normalized = thigh_vector / thigh_norm
        
        # Calcular ángulo interno (entre eje horizontal y vector del muslo)
        dot_product = np.dot(horizontal_ref, thigh_vector_normalized)
        dot_product = np.clip(dot_product, -1.0, 1.0)
        angle_internal = np.degrees(np.arccos(dot_product))
        
        # Convertir a formato clínico:
        # - 90° interno = 0° clínico (neutro)
        # - >90° interno = abducción positiva
        # - <90° interno = aducción (valores negativos, poco común)
        clinical_angle = abs(angle_internal - 90.0)
        
        return clinical_angle
    
    def calculate_symmetry_difference(self):
        """Calcula la diferencia de simetría entre caderas izquierda y derecha"""
        return abs(self.left_hip_angle - self.right_hip_angle)
    
    def get_landmarks_2d(self, landmark, frame_width, frame_height):
        """Convierte landmarks normalizados a coordenadas de píxeles"""
        return [int(landmark.x * frame_width), int(landmark.y * frame_height)]
    
    def _draw_performance_metrics(self, image, current_fps, current_processing_time):
        """Dibuja métricas de rendimiento en pantalla"""
        h, w = image.shape[:2]
        
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        avg_processing = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        panel_x = w - 220
        panel_y = 10
        
        # Fondo semitransparente
        overlay = image.copy()
        cv2.rectangle(overlay, (panel_x - 10, panel_y), (w - 10, panel_y + 120), 
                     self.color_cache['gray'], -1)
        cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)
        
        # Métricas
        cv2.putText(image, f"FPS: {current_fps:.1f} (avg: {avg_fps:.1f})", 
                   (panel_x, panel_y + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['green'], 1, cv2.LINE_4)
        
        cv2.putText(image, f"Latencia: {current_processing_time:.1f}ms", 
                   (panel_x, panel_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['yellow'], 1, cv2.LINE_4)
        
        cv2.putText(image, f"Frames: {self.frame_count}", 
                   (panel_x, panel_y + 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['white'], 1, cv2.LINE_4)
        
        # Indicador de modo
        mode_icons = {"CLEAN": "Clean", "FULL": "Full", "MINIMAL": "Min"}
        mode_colors = {
            "CLEAN": self.color_cache['green'],
            "FULL": self.color_cache['cyan'],
            "MINIMAL": self.color_cache['orange']
        }
        mode_text = f"Modo: {mode_icons.get(self.display_mode, '')}"
        cv2.putText(image, mode_text, 
                   (panel_x - 20, panel_y + 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, 
                   mode_colors.get(self.display_mode, self.color_cache['white']), 1, cv2.LINE_4)
    
    def process_frame(self, frame):
        """Procesa un frame y retorna el frame anotado"""
        start_time = time.time()
        self.frame_count += 1
        
        # Guardar dimensiones originales
        original_h, original_w = frame.shape[:2]
        
        # Reducir resolución para procesamiento
        small_frame = cv2.resize(frame, (self.processing_width, self.processing_height), 
                                interpolation=cv2.INTER_LINEAR)
        
        # Convertir a RGB
        image_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False
        
        # Procesar con MediaPipe
        results = self.pose.process(image_rgb)
        
        # Trabajar con resolución original para visualización
        image_rgb.flags.writeable = True
        image = frame.copy()
        
        if results.pose_landmarks:
            h, w = image.shape[:2]
            landmarks = results.pose_landmarks.landmark
            
            # Dibujar skeleton solo en modo FULL
            if self.display_mode == "FULL":
                mp_drawing.draw_landmarks(
                    image,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
                )
            
            # Procesar vista frontal (bilateral)
            self.process_frontal_view(image, landmarks, w, h)
        else:
            cv2.putText(image, "No se detecta persona", (50, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, self.color_cache['red'], 2, cv2.LINE_4)
        
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
    
    def process_frontal_view(self, image, landmarks, w, h):
        """Procesa vista frontal - Análisis de abducción/aducción bilateral de caderas"""
        # Obtener landmarks de ambas piernas
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        left_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
        left_ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE]
        
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        right_knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]
        right_ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE]
        
        # Convertir a coordenadas 2D
        left_hip_2d = self.get_landmarks_2d(left_hip, w, h)
        left_knee_2d = self.get_landmarks_2d(left_knee, w, h)
        left_ankle_2d = self.get_landmarks_2d(left_ankle, w, h)
        
        right_hip_2d = self.get_landmarks_2d(right_hip, w, h)
        right_knee_2d = self.get_landmarks_2d(right_knee, w, h)
        right_ankle_2d = self.get_landmarks_2d(right_ankle, w, h)
        
        # Calcular ángulos de abducción/aducción (ahora pasamos ambas caderas)
        left_angle = self.calculate_hip_abduction_angle(left_hip_2d, right_hip_2d, left_knee_2d)
        right_angle = self.calculate_hip_abduction_angle(left_hip_2d, right_hip_2d, right_knee_2d)
        
        # Actualizar estadísticas
        self.left_hip_angle = left_angle
        self.right_hip_angle = right_angle
        
        if left_angle > self.max_left_abduction:
            self.max_left_abduction = left_angle
        if right_angle > self.max_right_abduction:
            self.max_right_abduction = right_angle
        
        # ===== DIBUJAR VISUALIZACIÓN =====
        
        # Determinar qué pierna(s) dibujar según selección
        draw_left = self.selected_leg in ['left', 'both']
        draw_right = self.selected_leg in ['right', 'both']
        
        # Longitud de las líneas horizontales de referencia
        horizontal_line_length = 200
        
        if draw_left:
            # ===== EJE HORIZONTAL IZQUIERDO (brazo fijo del goniómetro) =====
            # Línea horizontal PURA que pasa por la cadera izquierda (paralela a borde de pantalla)
            left_horiz_start = (left_hip_2d[0] - horizontal_line_length, left_hip_2d[1])
            left_horiz_end = (left_hip_2d[0] + horizontal_line_length, left_hip_2d[1])
            cv2.line(image, left_horiz_start, left_horiz_end, 
                    self.color_cache['green'], 3, cv2.LINE_4)  # Verde - brazo fijo
            
            # Etiqueta del eje horizontal izquierdo
            cv2.putText(image, "0deg", 
                       (left_hip_2d[0] - horizontal_line_length + 10, left_hip_2d[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['green'], 2, cv2.LINE_4)
            
            # Puntos clave - PIERNA IZQUIERDA
            cv2.circle(image, left_hip_2d, 10, self.color_cache['yellow'], -1, cv2.LINE_4)   # CADERA (vértice)
            cv2.circle(image, left_knee_2d, 8, self.color_cache['cyan'], -1, cv2.LINE_4)     # RODILLA
            
            # Línea del muslo izquierdo (CADERA → RODILLA) - BRAZO MÓVIL
            cv2.line(image, left_hip_2d, left_knee_2d, self.color_cache['blue'], 4, cv2.LINE_4)
            
            # Pierna inferior izquierda - solo en CLEAN y FULL
            if self.display_mode != "MINIMAL":
                cv2.line(image, left_knee_2d, left_ankle_2d, self.color_cache['blue'], 2, cv2.LINE_4)
                cv2.circle(image, left_ankle_2d, 6, self.color_cache['blue'], -1, cv2.LINE_4)
            
            # Mostrar ángulo y tipo de movimiento
            left_color = self.get_hip_abduction_color(left_angle)
            cv2.putText(image, f"{left_angle:.1f}deg", 
                       (left_hip_2d[0] - 100, left_hip_2d[1] - 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.4, left_color, 3, cv2.LINE_4)
            
            # Mostrar tipo de ejercicio
            exercise_color = self.color_cache['orange'] if self.exercise_type == "abduccion" else \
                           self.color_cache['magenta']
            cv2.putText(image, self.exercise_type.upper(), 
                       (left_hip_2d[0] - 100, left_hip_2d[1] + 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, exercise_color, 2, cv2.LINE_4)
        
        if draw_right:
            # ===== EJE HORIZONTAL DERECHO (brazo fijo del goniómetro) =====
            # Línea horizontal PURA que pasa por la cadera derecha (paralela a borde de pantalla)
            right_horiz_start = (right_hip_2d[0] - horizontal_line_length, right_hip_2d[1])
            right_horiz_end = (right_hip_2d[0] + horizontal_line_length, right_hip_2d[1])
            cv2.line(image, right_horiz_start, right_horiz_end, 
                    self.color_cache['green'], 3, cv2.LINE_4)  # Verde - brazo fijo
            
            # Etiqueta del eje horizontal derecho
            cv2.putText(image, "0deg", 
                       (right_hip_2d[0] + horizontal_line_length - 60, right_hip_2d[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['green'], 2, cv2.LINE_4)
            
            # Puntos clave - PIERNA DERECHA
            cv2.circle(image, right_hip_2d, 10, self.color_cache['yellow'], -1, cv2.LINE_4)  # CADERA (vértice)
            cv2.circle(image, right_knee_2d, 8, self.color_cache['cyan'], -1, cv2.LINE_4)    # RODILLA
            
            # Línea del muslo derecho (CADERA → RODILLA) - BRAZO MÓVIL
            cv2.line(image, right_hip_2d, right_knee_2d, self.color_cache['blue'], 4, cv2.LINE_4)
            
            # Pierna inferior derecha - solo en CLEAN y FULL
            if self.display_mode != "MINIMAL":
                cv2.line(image, right_knee_2d, right_ankle_2d, self.color_cache['blue'], 2, cv2.LINE_4)
                cv2.circle(image, right_ankle_2d, 6, self.color_cache['blue'], -1, cv2.LINE_4)
            
            # Mostrar ángulo y tipo de movimiento
            right_color = self.get_hip_abduction_color(right_angle)
            cv2.putText(image, f"{right_angle:.1f}deg", 
                       (right_hip_2d[0] + 20, right_hip_2d[1] - 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.4, right_color, 3, cv2.LINE_4)
            
            # Mostrar tipo de ejercicio
            exercise_color = self.color_cache['orange'] if self.exercise_type == "abduccion" else \
                           self.color_cache['magenta']
            cv2.putText(image, self.exercise_type.upper(), 
                       (right_hip_2d[0] + 20, right_hip_2d[1] + 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, exercise_color, 2, cv2.LINE_4)
        
        # Panel de información
        self.draw_info_panel(image, w, h)
    
    def draw_info_panel(self, image, w, h):
        """Dibuja panel informativo con análisis de simetría"""
        # Panel superior con fondo semi-transparente
        panel_height = 260
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (w, panel_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
        
        # Título adaptado según pierna seleccionada
        if self.selected_leg == 'left':
            title = f"ANALISIS DE CADERA IZQUIERDA - {self.exercise_type.upper()} (FRONTAL)"
        elif self.selected_leg == 'right':
            title = f"ANALISIS DE CADERA DERECHA - {self.exercise_type.upper()} (FRONTAL)"
        else:
            title = f"ANALISIS DE CADERA - {self.exercise_type.upper()} BILATERAL (FRONTAL)"
        
        cv2.putText(image, title, (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color_cache['green'], 2, cv2.LINE_4)
        
        # Mostrar información según pierna seleccionada
        if self.selected_leg in ['left', 'both']:
            # Ángulos cadera izquierda
            left_color = self.get_hip_abduction_color(self.left_hip_angle)
            cv2.putText(image, f"Cadera Izq: {self.left_hip_angle:.1f}deg", (20, 85),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, left_color, 2, cv2.LINE_4)
            cv2.putText(image, f"Max: {self.max_left_abduction:.1f}deg", (20, 115),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['light_gray'], 2, cv2.LINE_4)
        
        if self.selected_leg in ['right', 'both']:
            # Ángulos cadera derecha
            x_offset = w//2 + 20 if self.selected_leg == 'both' else 20
            y_offset = 0 if self.selected_leg == 'both' else 170
            
            right_color = self.get_hip_abduction_color(self.right_hip_angle)
            cv2.putText(image, f"Cadera Der: {self.right_hip_angle:.1f}deg", (x_offset, 85 + y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, right_color, 2, cv2.LINE_4)
            cv2.putText(image, f"Max: {self.max_right_abduction:.1f}deg", (x_offset, 115 + y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['light_gray'], 2, cv2.LINE_4)
        
        # Análisis de simetría (solo si ambas piernas están activas)
        if self.selected_leg == 'both':
            diff = self.calculate_symmetry_difference()
            
            if diff < 5:
                diff_color = self.color_cache['green']
                diff_status = "EXCELENTE"
            elif diff < 10:
                diff_color = self.color_cache['orange']
                diff_status = "ACEPTABLE"
            else:
                diff_color = self.color_cache['red']
                diff_status = "REVISAR"
            
            cv2.putText(image, f"Diferencia de simetria: {diff:.1f}deg [{diff_status}]", (20, 180),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.65, diff_color, 2, cv2.LINE_4)
        
        # Información del ejercicio seleccionado
        exercise_color = self.color_cache['orange'] if self.exercise_type == "abduccion" else \
                        self.color_cache['magenta']
        cv2.putText(image, f"Ejercicio: {self.exercise_type.upper()}", 
                   (20, 210),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise_color, 2, cv2.LINE_4)
        
        # Guía de ROM
        cv2.putText(image, "ROM normal: 0-45deg", 
                   (20, 235),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['light_gray'], 1, cv2.LINE_4)
        
        # Instrucciones inferiores
        instruction_text = f"Realiza {self.exercise_type} | 'R' reiniciar | 'M' modo | 'Q' salir"
        cv2.putText(image, instruction_text, 
                   (20, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['white'], 2, cv2.LINE_4)
    
    def get_hip_abduction_color(self, angle):
        """Retorna color según ángulo de abducción de cadera"""
        if angle < 10:
            return self.color_cache['white']
        elif angle < 25:
            return self.color_cache['yellow']
        elif angle < 45:
            return self.color_cache['orange']
        else:
            return self.color_cache['green']
    
    def reset_stats(self):
        """Reinicia estadísticas"""
        self.left_hip_angle = 0
        self.right_hip_angle = 0
        self.max_left_abduction = 0
        self.max_right_abduction = 0
        self.fps_history.clear()
        self.processing_times.clear()
        self.frame_count = 0
        print("[OK] Estadisticas reiniciadas")
    
    def get_performance_summary(self):
        """Retorna resumen de métricas de rendimiento"""
        if not self.fps_history:
            return {
                'total_frames': 0,
                'avg_fps': 0,
                'min_fps': 0,
                'max_fps': 0,
                'avg_processing_time': 0
            }
        
        return {
            'total_frames': self.frame_count,
            'avg_fps': sum(self.fps_history) / len(self.fps_history),
            'min_fps': min(self.fps_history),
            'max_fps': max(self.fps_history),
            'avg_processing_time': sum(self.processing_times) / len(self.processing_times)
        }
    
    def release(self):
        """Libera recursos de MediaPipe"""
        self.pose.close()


def main():
    """Función principal"""
    print("=" * 70)
    print("ANALISIS DE ABDUCCION/ADUCCION DE CADERAS - VISTA FRONTAL")
    print("=" * 70)
    print("\n[*] OPTIMIZACIONES ACTIVADAS:")
    print("   - Procesamiento en 640x480 (upscaling a 720p para display)")
    print("   - Dibujos OpenCV optimizados (LINE_4)")
    print("   - Cache de colores")
    print("   - Profiling de FPS y latencia en tiempo real")
    print("\n[*] MODOS DE VISUALIZACION:")
    print("   - CLEAN (Predeterminado): Solo lineas biomecanicas")
    print("   - FULL: Con skeleton completo de MediaPipe")
    print("   - MINIMAL: Maximo rendimiento")
    
    # ===== SELECCIÓN DE TIPO DE EJERCICIO =====
    print("\n" + "=" * 70)
    print("[*] SELECCION DE TIPO DE EJERCICIO:")
    print("=" * 70)
    print("   1. ABDUCCION (separar pierna del cuerpo)")
    print("   2. ADUCCION (acercar pierna al cuerpo)")
    print()
    
    exercise_type = 'abduccion'  # Valor por defecto
    while True:
        try:
            choice = input("Selecciona el tipo de ejercicio (1/2) [Por defecto: 1]: ").strip()
            
            if choice == '' or choice == '1':
                exercise_type = 'abduccion'
                print("[OK] Ejercicio ABDUCCION seleccionado")
                break
            elif choice == '2':
                exercise_type = 'aduccion'
                print("[OK] Ejercicio ADUCCION seleccionado")
                break
            else:
                print("[ERROR] Opcion invalida. Por favor ingresa 1 o 2.")
        except KeyboardInterrupt:
            print("\n[*] Operacion cancelada por el usuario")
            return
        except Exception as e:
            print(f"[ERROR] Error en la seleccion: {e}")
            print("[*] Usando opcion por defecto (ABDUCCION)")
            exercise_type = 'abduccion'
            break
    
    # ===== SELECCIÓN DE PIERNA A ANALIZAR =====
    print("\n" + "=" * 70)
    print("[*] SELECCION DE PIERNA A ANALIZAR:")
    print("=" * 70)
    print("   1. Pierna IZQUIERDA solamente")
    print("   2. Pierna DERECHA solamente")
    print("   3. AMBAS piernas (analisis bilateral con simetria)")
    print()
    
    selected_leg = 'both'  # Valor por defecto
    while True:
        try:
            choice = input("Selecciona una opcion (1/2/3) [Por defecto: 3]: ").strip()
            
            if choice == '' or choice == '3':
                selected_leg = 'both'
                print("[OK] Analisis BILATERAL seleccionado (ambas piernas)")
                break
            elif choice == '1':
                selected_leg = 'left'
                print("[OK] Analisis de PIERNA IZQUIERDA seleccionado")
                break
            elif choice == '2':
                selected_leg = 'right'
                print("[OK] Analisis de PIERNA DERECHA seleccionado")
                break
            else:
                print("[ERROR] Opcion invalida. Por favor ingresa 1, 2 o 3.")
        except KeyboardInterrupt:
            print("\n[*] Operacion cancelada por el usuario")
            return
        except Exception as e:
            print(f"[ERROR] Error en la seleccion: {e}")
            print("[*] Usando opcion por defecto (AMBAS piernas)")
            selected_leg = 'both'
            break
    
    print("\n[*] INSTRUCCIONES:")
    print("   1. Colocate de FRENTE a la camara")
    
    if exercise_type == 'abduccion':
        if selected_leg == 'both':
            print("   2. SEPARA AMBAS piernas lateralmente (abduccion)")
        else:
            leg_name = "IZQUIERDA" if selected_leg == 'left' else "DERECHA"
            print(f"   2. SEPARA la pierna {leg_name} lateralmente (abduccion)")
    else:  # aduccion
        if selected_leg == 'both':
            print("   2. ACERCA AMBAS piernas hacia el cuerpo (aduccion)")
        else:
            leg_name = "IZQUIERDA" if selected_leg == 'left' else "DERECHA"
            print(f"   2. ACERCA la pierna {leg_name} hacia el cuerpo (aduccion)")
    
    if selected_leg == 'both':
        print("   3. El sistema mide AMBAS caderas y compara simetria")
    else:
        leg_name = "IZQUIERDA" if selected_leg == 'left' else "DERECHA"
        print(f"   3. El sistema mide solo la cadera {leg_name}")
    
    print("   4. Presiona 'M' para cambiar modo de visualizacion")
    print("   5. Presiona 'R' para reiniciar estadisticas")
    print("   6. Presiona 'Q' para salir")
    print("\n[*] SISTEMA GONIOMETRO (METODO CLINICO CORRECTO):")
    print("   - VERTICE: Cadera (hip)")
    print("   - BRAZO FIJO: Eje HORIZONTAL PURO (paralelo al borde de pantalla)")
    print("   - BRAZO MOVIL: Linea del muslo (CADERA → RODILLA)")
    print("   - Medicion interna: 90deg = neutro (perpendicular al eje horizontal)")
    print("   - Mostrado al usuario: 0deg = neutro, valores positivos = abduccion")
    print("\n[*] INTERPRETACION DE ANGULOS:")
    print("   - 0deg = Piernas VERTICALES (posicion neutra - 90deg interno)")
    print("   - 25deg = Abduccion moderada (115deg interno)")
    print("   - 45deg = Abduccion BUENA/ROM normal (135deg interno)")
    print("   - 90deg = Pierna horizontal - teorico (180deg interno)")
    
    if selected_leg == 'both':
        print("\n[*] ANALISIS DE SIMETRIA:")
        print("   - Verde: Diferencia < 5deg (EXCELENTE)")
        print("   - Naranja: Diferencia 5-10deg (ACEPTABLE)")
        print("   - Rojo: Diferencia > 10deg (REVISAR - posible asimetria)")
    
    print("\n[*] ROM NORMAL: 0-45deg (clinico)")
    print("=" * 70)
    
    # Inicializar analizador con la pierna y ejercicio seleccionados
    analyzer = HipFrontalAnalyzer(
        processing_width=640, 
        processing_height=480, 
        selected_leg=selected_leg,
        exercise_type=exercise_type
    )
    
    # Inicializar cámara
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("\n[ERROR] No se pudo abrir la camara")
        return
    
    # Configurar resolución
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("\n[OK] Camara iniciada correctamente")
    print("[*] Procesando video...")
    print("[*] Metricas de rendimiento visibles en esquina superior derecha\n")
    
    while cap.isOpened():
        ret, frame = cap.read()
        
        if not ret:
            print("\n[ERROR] No se pudo leer el frame")
            break
        
        # Procesar frame
        annotated_frame = analyzer.process_frame(frame)
        
        # Mostrar resultado
        cv2.imshow('Analisis de Abduccion/Aduccion de Caderas - Frontal', annotated_frame)
        
        # Controles de teclado
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q') or key == ord('Q'):
            print("\n[*] Cerrando aplicacion...")
            break
        elif key == ord('r') or key == ord('R'):
            analyzer.reset_stats()
        elif key == ord('m') or key == ord('M'):
            analyzer.toggle_display_mode()
    
    # Liberar recursos
    cap.release()
    cv2.destroyAllWindows()
    analyzer.release()
    
    # Mostrar resumen
    perf = analyzer.get_performance_summary()
    
    print("\n" + "=" * 70)
    print("[OK] Aplicacion cerrada correctamente")
    print("=" * 70)
    print(f"\n[*] RESUMEN DE RENDIMIENTO:")
    print(f"   - Total de frames procesados: {perf['total_frames']}")
    print(f"   - FPS promedio: {perf['avg_fps']:.1f}")
    print(f"   - FPS minimo: {perf['min_fps']:.1f}")
    print(f"   - FPS maximo: {perf['max_fps']:.1f}")
    print(f"   - Latencia promedio: {perf['avg_processing_time']:.2f}ms")
    
    print(f"\n[*] ESTADISTICAS BIOMECANICAS:")
    
    # Mostrar estadísticas según pierna seleccionada
    if analyzer.selected_leg in ['left', 'both']:
        print(f"   - Abduccion maxima cadera izquierda: {analyzer.max_left_abduction:.1f}deg")
    if analyzer.selected_leg in ['right', 'both']:
        print(f"   - Abduccion maxima cadera derecha: {analyzer.max_right_abduction:.1f}deg")
    
    # Análisis de simetría (solo si ambas piernas)
    if analyzer.selected_leg == 'both':
        diff = abs(analyzer.max_left_abduction - analyzer.max_right_abduction)
        print(f"   - Diferencia entre caderas: {diff:.1f}deg")
        
        if diff < 5:
            print(f"   - Evaluacion de simetria: EXCELENTE")
        elif diff < 10:
            print(f"   - Evaluacion de simetria: ACEPTABLE")
        else:
            print(f"   - Evaluacion de simetria: REVISAR - Asimetria detectada")
    
    # Evaluación del ROM según pierna(s) analizada(s)
    if analyzer.selected_leg == 'both':
        avg_rom = (analyzer.max_left_abduction + analyzer.max_right_abduction) / 2
        rom_label = "promedio"
    elif analyzer.selected_leg == 'left':
        avg_rom = analyzer.max_left_abduction
        rom_label = "izquierda"
    else:  # right
        avg_rom = analyzer.max_right_abduction
        rom_label = "derecha"
    
    if avg_rom >= 40:
        print(f"   - Evaluacion ROM {rom_label}: EXCELENTE rango de abduccion")
    elif avg_rom >= 30:
        print(f"   - Evaluacion ROM {rom_label}: BUENA abduccion")
    elif avg_rom >= 20:
        print(f"   - Evaluacion ROM {rom_label}: LIMITADA - Revisar")
    else:
        print(f"   - Evaluacion ROM {rom_label}: REDUCIDA - Consultar especialista")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
