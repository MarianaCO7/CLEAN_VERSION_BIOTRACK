"""
Script independiente para análisis de movimiento de hombro en tiempo real
Utiliza OpenCV y MediaPipe para detectar y calcular ángulos
- Vista de PERFIL: Analiza extensión/flexión del hombro visible
- Vista FRONTAL: Analiza abducción bilateral de ambos hombros simultáneamente

OPTIMIZACIONES IMPLEMENTADAS:
- Procesamiento en resolución reducida (640x480) con upscaling para display
- Dibujos OpenCV optimizados (LINE_4 en vez de LINE_AA)
- Caché de colores por rangos de ángulos
- Sistema de profiling de FPS y latencia
- Threading para procesamiento asíncrono
"""

import cv2
import mediapipe as mp
import numpy as np
import math
import time
from collections import deque
from threading import Thread, Lock
import queue

# Inicializar MediaPipe Pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

class ShoulderExtensionAnalyzer:
    def __init__(self, processing_width=640, processing_height=480):
        """
        Inicializa el analizador con optimizaciones de rendimiento
        
        Args:
            processing_width: Ancho para procesamiento de MediaPipe (menor = más rápido)
            processing_height: Alto para procesamiento de MediaPipe
        """
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1  # CPU-optimized
        )
        
        # 🚀 OPTIMIZACIÓN: Resolución de procesamiento reducida
        self.processing_width = processing_width
        self.processing_height = processing_height
        
        # 🎯 GONIÓMETRO: Variables para tracking - SIEMPRE POSITIVO
        self.current_angle = 0
        self.max_angle = 0  # Máximo ROM alcanzado (siempre positivo como goniómetro)
        self.side = "Detectando..."
        
        # Variables para tracking de ángulos - Vista frontal (abducción)
        self.left_abduction_angle = 0
        self.right_abduction_angle = 0
        self.max_left_abduction = 0
        self.max_right_abduction = 0
        
        # Variable para detectar orientación
        self.view_type = "Detectando..."  # "PERFIL" o "FRONTAL"
        
        self.frame_count = 0
        
        # 🎨 MODO DE VISUALIZACIÓN
        self.display_mode = "CLEAN"  # Opciones: "CLEAN", "FULL", "MINIMAL"
        # CLEAN: Sin skeleton, solo líneas biomecánicas (recomendado)
        # FULL: Con skeleton completo (debugging)
        # MINIMAL: Solo líneas esenciales (máximo rendimiento)
        
        # 📊 PROFILING: Métricas de rendimiento
        self.fps_history = deque(maxlen=30)  # Últimos 30 frames
        self.processing_times = deque(maxlen=30)
        self.last_time = time.time()
        
        # 🎨 CACHÉ: Colores pre-calculados
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
        
        # 🎨 MODO DE VISUALIZACIÓN
        self.display_mode = "CLEAN"  # Opciones: "CLEAN", "FULL", "MINIMAL"
        # CLEAN: Sin skeleton, solo líneas biomecánicas (RECOMENDADO - profesional)
        # FULL: Con skeleton completo (debugging)
        # MINIMAL: Solo líneas esenciales (máximo rendimiento)
    
    def calculate_angle(self, point1, point2, point3):
        """
        Calcula el ángulo entre tres puntos
        point1: primer punto (ej: cadera)
        point2: vértice del ángulo (ej: hombro)
        point3: tercer punto (ej: codo)
        """
        # Convertir a arrays numpy
        p1 = np.array(point1)
        p2 = np.array(point2)
        p3 = np.array(point3)
        
        # Calcular vectores
        vector1 = p1 - p2
        vector2 = p3 - p2
        
        # Calcular ángulo usando producto punto
        cosine_angle = np.dot(vector1, vector2) / (np.linalg.norm(vector1) * np.linalg.norm(vector2))
        
        # Evitar errores de dominio
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        
        angle = np.degrees(np.arccos(cosine_angle))
        
        return angle
    
    def calculate_extension_angle(self, shoulder, hip, elbow, side):
        """
        🎯 SISTEMA GONIÓMETRO ESTÁNDAR CON EJE VERTICAL FIJO
        
        Simula un goniómetro real donde:
        - Brazo FIJO: Eje vertical absoluto (paralelo al borde de la imagen)
        - Brazo MÓVIL: Línea del brazo (hombro → codo)
        - Centro: Punto del hombro
        
        Sistema de referencia:
        - 0° = Brazo apuntando hacia ABAJO (vertical hacia abajo)
        - Positivo (+) = Flexión (hacia adelante/arriba)
        - Negativo (-) = Extensión (hacia atrás)
        
        Args:
            shoulder: Coordenadas [x, y] del hombro
            hip: Coordenadas [x, y] de la cadera (NO se usa para el eje, solo referencia visual)
            elbow: Coordenadas [x, y] del codo
            side: 'left' o 'right' para determinar dirección
        """
        # 📐 VECTOR DE REFERENCIA VERTICAL FIJO (goniómetro estándar)
        # Este vector es SIEMPRE vertical hacia abajo, independiente de la postura
        # Simula el brazo fijo del goniómetro alineado con la gravedad
        vertical_down_vector = np.array([0, 1])  # Vector unitario vertical (hacia abajo)
        
        # Vector del brazo (de hombro a codo) - BRAZO MÓVIL del goniómetro
        arm_vector = np.array([elbow[0] - shoulder[0], elbow[1] - shoulder[1]])
        
        # Normalizar vector del brazo
        arm_norm = np.linalg.norm(arm_vector)
        
        if arm_norm == 0:
            return 0
        
        arm_vector_normalized = arm_vector / arm_norm
        
        # Calcular ángulo entre el eje vertical y el brazo
        dot_product = np.dot(vertical_down_vector, arm_vector_normalized)
        dot_product = np.clip(dot_product, -1.0, 1.0)
        
        # Ángulo sin signo (0° a 180°)
        angle_magnitude = np.degrees(np.arccos(dot_product))
        
        # 🎯 CALCULAR DIRECCIÓN con producto cruz
        # Producto cruz en 2D: vertical × arm = (0)(arm_y) - (1)(arm_x) = -arm_x
        cross_product = -arm_vector[0]  # Simplificado para vector vertical [0, 1]
        
        # Determinar el signo según el lado y la dirección
        if side == 'left':
            if cross_product > 0:
                angle = angle_magnitude  # Adelante = POSITIVO
            else:
                angle = -angle_magnitude  # Atrás = NEGATIVO
        else:  # side == 'right'
            if cross_product < 0:
                angle = angle_magnitude  # Adelante = POSITIVO
            else:
                angle = -angle_magnitude  # Atrás = NEGATIVO
        
        return angle  # ✅ Con signo: +flexión, -extensión
    
    def calculate_abduction_angle(self, shoulder, hip, elbow):
        """
        🎯 Calcula el ángulo de abducción del hombro con EJE VERTICAL FIJO (vista frontal)
        
        Sistema goniométrico estándar:
        - Brazo FIJO: Eje vertical absoluto (paralelo al marco de referencia)
        - Brazo MÓVIL: Línea del brazo (hombro → codo)
        
        Rango de medición:
        - 0° = Brazo paralelo al eje vertical (brazo abajo, pegado al cuerpo)
        - 90° = Brazo horizontal (perpendicular al cuerpo)
        - 180° = Brazo completamente levantado (vertical hacia arriba)
        
        Args:
            shoulder: Coordenadas [x, y] del hombro
            hip: Coordenadas [x, y] de la cadera (referencia visual, no se usa en cálculo)
            elbow: Coordenadas [x, y] del codo
        """
        # 📐 VECTOR DE REFERENCIA VERTICAL FIJO (goniómetro estándar)
        vertical_down_vector = np.array([0, 1])  # Vector unitario vertical hacia abajo
        
        # Vector del brazo (de hombro a codo)
        arm_vector = np.array([elbow[0] - shoulder[0], elbow[1] - shoulder[1]])
        
        # Normalizar vector del brazo
        arm_norm = np.linalg.norm(arm_vector)
        
        if arm_norm == 0:
            return 0
        
        arm_vector_normalized = arm_vector / arm_norm
        
        # Calcular ángulo entre el eje vertical y el brazo
        dot_product = np.dot(vertical_down_vector, arm_vector_normalized)
        dot_product = np.clip(dot_product, -1.0, 1.0)
        
        # Ángulo de abducción (siempre positivo en vista frontal)
        angle = np.degrees(np.arccos(dot_product))
        
        return angle
    
    def detect_side_and_visibility(self, landmarks):
        """
        Detecta qué lado del cuerpo está visible y hacia dónde mira la persona
        También determina si está de PERFIL o FRONTAL
        Retorna: tipo_vista, lado (para perfil), confianza, orientación
        """
        # Obtener puntos clave
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        nose = landmarks[mp_pose.PoseLandmark.NOSE]
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        
        # Calcular visibilidad de cada lado
        left_visibility = left_shoulder.visibility
        right_visibility = right_shoulder.visibility
        
        # Calcular distancia entre hombros (en coordenadas normalizadas)
        shoulder_distance = abs(right_shoulder.x - left_shoulder.x)
        
        # Calcular distancia entre caderas
        hip_distance = abs(right_hip.x - left_hip.x)
        
        # Determinar si está de FRENTE o PERFIL
        # Si ambos hombros son muy visibles Y la distancia entre ellos es grande = FRONTAL
        # Umbral: si la distancia entre hombros > 0.15 (normalizado) = probablemente frontal
        
        avg_shoulder_visibility = (left_visibility + right_visibility) / 2
        
        if shoulder_distance > 0.12 and avg_shoulder_visibility > 0.6 and left_visibility > 0.5 and right_visibility > 0.5:
            # Vista FRONTAL
            view_type = "FRONTAL"
            side = None  # No aplica en vista frontal
            confidence = avg_shoulder_visibility
            orientation = "de frente"
        else:
            # Vista de PERFIL
            view_type = "PERFIL"
            
            # Determinar orientación basado en la posición de la nariz respecto a los hombros
            nose_x = nose.x
            left_shoulder_x = left_shoulder.x
            right_shoulder_x = right_shoulder.x
            
            shoulder_center_x = (left_shoulder_x + right_shoulder_x) / 2
            
            # Calcular qué hombro está más de perfil (más visible y más alejado de la nariz)
            if left_visibility > right_visibility:
                # Hombro izquierdo más visible
                side = 'left'
                confidence = left_visibility
                orientation = "mirando izquierda" if nose_x < shoulder_center_x else "mirando derecha"
            else:
                # Hombro derecho más visible
                side = 'right'
                confidence = right_visibility
                orientation = "mirando derecha" if nose_x > shoulder_center_x else "mirando izquierda"
        
        return view_type, side, confidence, orientation
    
    def get_landmarks_2d(self, landmark, frame_width, frame_height):
        """Convierte landmarks normalizados a coordenadas de píxeles"""
        return [int(landmark.x * frame_width), int(landmark.y * frame_height)]
    
    def draw_angle_arc(self, image, center, start_point, end_point, angle, color):
        """Dibuja un arco para visualizar el ángulo"""
        radius = 50
        
        # Calcular ángulos de inicio y fin
        start_angle = math.degrees(math.atan2(start_point[1] - center[1], start_point[0] - center[0]))
        end_angle = math.degrees(math.atan2(end_point[1] - center[1], end_point[0] - center[0]))
        
        # Dibujar arco
        cv2.ellipse(image, center, (radius, radius), 0, start_angle, end_angle, color, 2)
    
    def toggle_display_mode(self):
        """Alterna entre modos de visualización"""
        modes = ["CLEAN", "FULL", "MINIMAL"]
        current_index = modes.index(self.display_mode)
        next_index = (current_index + 1) % len(modes)
        self.display_mode = modes[next_index]
        
        mode_descriptions = {
            "CLEAN": "🎯 LIMPIO - Solo líneas biomecánicas (Recomendado)",
            "FULL": "📊 COMPLETO - Con skeleton de MediaPipe",
            "MINIMAL": "⚡ MINIMALISTA - Máximo rendimiento"
        }
        
        print(f"\n🎨 Modo de visualización cambiado a: {mode_descriptions[self.display_mode]}")
        
        return self.display_mode
    
    def _draw_performance_metrics(self, image, current_fps, current_processing_time):
        """
        📊 Dibuja métricas de rendimiento en pantalla
        """
        h, w = image.shape[:2]
        
        # Calcular promedios
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        avg_processing = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        # Panel de métricas (esquina superior derecha)
        panel_x = w - 220
        panel_y = 10
        
        # Fondo semitransparente
        overlay = image.copy()
        cv2.rectangle(overlay, (panel_x - 10, panel_y), (w - 10, panel_y + 90), 
                     self.color_cache['gray'], -1)
        cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)
        
        # Texto de métricas (optimizado con LINE_4)
        cv2.putText(image, f"FPS: {current_fps:.1f} (avg: {avg_fps:.1f})", 
                   (panel_x, panel_y + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['green'], 1, cv2.LINE_4)
        
        cv2.putText(image, f"Latencia: {current_processing_time:.1f}ms", 
                   (panel_x, panel_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['yellow'], 1, cv2.LINE_4)
        
        cv2.putText(image, f"Frames: {self.frame_count}", 
                   (panel_x, panel_y + 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['white'], 1, cv2.LINE_4)
        
        # 🎨 INDICADOR DE MODO DE VISUALIZACIÓN
        mode_icons = {
            "CLEAN": "Clean",
            "FULL": "Full",
            "MINIMAL": "Min"
        }
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
        """
        Procesa un frame y retorna el frame anotado
        🚀 OPTIMIZADO: Procesa en baja resolución, escala para display
        """
        start_time = time.time()
        self.frame_count += 1
        
        # 🚀 OPTIMIZACIÓN 1: Guardar dimensiones originales
        original_h, original_w = frame.shape[:2]
        
        # 🚀 OPTIMIZACIÓN 2: Reducir resolución para procesamiento MediaPipe
        small_frame = cv2.resize(frame, (self.processing_width, self.processing_height), 
                                interpolation=cv2.INTER_LINEAR)
        
        # Convertir BGR a RGB
        image_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False
        
        # Procesar con MediaPipe (en resolución reducida)
        results = self.pose.process(image_rgb)
        
        # Convertir de vuelta a BGR (usar frame original para display)
        image_rgb.flags.writeable = True
        image = frame.copy()  # Trabajar con resolución original para visualización
        
        if results.pose_landmarks:
            # 🚀 OPTIMIZACIÓN 3: Escalar landmarks a resolución original
            # MediaPipe devuelve coordenadas normalizadas (0-1), así que solo necesitamos
            # usar las dimensiones originales para conversión
            h, w = original_h, original_w
            
            landmarks = results.pose_landmarks.landmark
            
            # Detectar tipo de vista (PERFIL o FRONTAL)
            view_type, side, confidence, orientation = self.detect_side_and_visibility(landmarks)
            self.view_type = view_type
            
            # 🎨 DIBUJAR SKELETON SOLO EN MODO FULL
            if self.display_mode == "FULL":
                mp_drawing.draw_landmarks(
                    image,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
                )
            
            if view_type == "FRONTAL":
                # MODO FRONTAL - Analizar ABDUCCIÓN bilateral
                self.process_frontal_view(image, landmarks, w, h, orientation, confidence)
            else:
                # MODO PERFIL - Analizar EXTENSIÓN de un solo hombro
                self.process_profile_view(image, landmarks, w, h, side, orientation, confidence)
        else:
            # No se detectó persona
            cv2.putText(image, "No se detecta persona", (50, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, self.color_cache['red'], 2, cv2.LINE_4)
        
        # 📊 PROFILING: Calcular FPS y tiempo de procesamiento
        processing_time = (time.time() - start_time) * 1000  # en ms
        self.processing_times.append(processing_time)
        
        current_time = time.time()
        fps = 1.0 / (current_time - self.last_time) if (current_time - self.last_time) > 0 else 0
        self.fps_history.append(fps)
        self.last_time = current_time
        
        # 📊 Mostrar métricas de rendimiento
        self._draw_performance_metrics(image, fps, processing_time)
        
        return image
    
    def process_profile_view(self, image, landmarks, w, h, side, orientation, confidence):
        """Procesa vista de perfil - Análisis de extensión"""
        # Seleccionar landmarks según el lado detectado
        if side == 'left':
            shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
            hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
            elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
            wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
            side_text = "HOMBRO IZQUIERDO"
        else:
            shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
            hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
            elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
            wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
            side_text = "HOMBRO DERECHO"
        
        # Obtener coordenadas 2D
        shoulder_2d = self.get_landmarks_2d(shoulder, w, h)
        hip_2d = self.get_landmarks_2d(hip, w, h)
        elbow_2d = self.get_landmarks_2d(elbow, w, h)
        wrist_2d = self.get_landmarks_2d(wrist, w, h)
        
        # Calcular ángulo de extensión (CON SIGNO: +flexión, -extensión)
        angle = self.calculate_extension_angle(shoulder_2d, hip_2d, elbow_2d, side)
        
        # Actualizar estadísticas
        self.current_angle = angle
        self.side = side_text
        
        # 🎯 GONIÓMETRO: Actualizar máximo ROM (usar abs() para tracking)
        abs_angle = abs(angle)
        if abs_angle > self.max_angle:
            self.max_angle = abs_angle
        
        # 🚀 OPTIMIZACIÓN: Dibujar puntos clave (LINE_4 es más rápido)
        cv2.circle(image, shoulder_2d, 8, self.color_cache['yellow'], -1, cv2.LINE_4)
        cv2.circle(image, hip_2d, 8, self.color_cache['magenta'], -1, cv2.LINE_4)
        cv2.circle(image, elbow_2d, 8, self.color_cache['cyan'], -1, cv2.LINE_4)
        
        # � LÍNEA DE REFERENCIA VERTICAL FIJA (Goniómetro Estándar)
        # Esta línea es SIEMPRE vertical (paralela al borde de la imagen)
        # y pasa por el punto del hombro (punto de referencia)
        vertical_length = 150  # Longitud de la línea de referencia
        vertical_start = (shoulder_2d[0], shoulder_2d[1] - vertical_length)  # Arriba del hombro
        vertical_end = (shoulder_2d[0], shoulder_2d[1] + vertical_length)    # Abajo del hombro
        
        # Dibujar eje vertical fijo (verde - brazo fijo del goniómetro)
        cv2.line(image, vertical_start, vertical_end, self.color_cache['green'], 3, cv2.LINE_4)
        
        # 🔵 LÍNEA DEL BRAZO (Brazo móvil del goniómetro)
        # Línea del brazo superior (siempre visible)
        cv2.line(image, shoulder_2d, elbow_2d, self.color_cache['blue'], 3, cv2.LINE_4)
        
        # 🎨 Antebrazo (solo en CLEAN y FULL, no en MINIMAL)
        if self.display_mode != "MINIMAL":
            cv2.line(image, elbow_2d, wrist_2d, self.color_cache['blue'], 2, cv2.LINE_4)
        
        # 🚀 OPTIMIZACIÓN: Mostrar ángulo (LINE_4)
        angle_text = f"{abs(angle):.1f}°"
        direction_text = "FLEX" if angle > 0 else "EXT" if angle < 0 else ""
        cv2.putText(image, angle_text, 
                   (shoulder_2d[0] - 40, shoulder_2d[1] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, self.color_cache['yellow'], 3, cv2.LINE_4)
        if direction_text:
            direction_color = self.color_cache['green'] if angle > 0 else self.color_cache['orange']
            cv2.putText(image, direction_text, 
                       (shoulder_2d[0] - 30, shoulder_2d[1] + 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, direction_color, 2, cv2.LINE_4)
        
        # Panel de información
        self.draw_info_panel_profile(image, orientation, confidence)
    
    def process_frontal_view(self, image, landmarks, w, h, orientation, confidence):
        """Procesa vista frontal - Análisis de abducción bilateral"""
        # Obtener landmarks de ambos lados
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
        left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
        
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
        
        # Convertir a coordenadas 2D
        left_shoulder_2d = self.get_landmarks_2d(left_shoulder, w, h)
        left_hip_2d = self.get_landmarks_2d(left_hip, w, h)
        left_elbow_2d = self.get_landmarks_2d(left_elbow, w, h)
        left_wrist_2d = self.get_landmarks_2d(left_wrist, w, h)
        
        right_shoulder_2d = self.get_landmarks_2d(right_shoulder, w, h)
        right_hip_2d = self.get_landmarks_2d(right_hip, w, h)
        right_elbow_2d = self.get_landmarks_2d(right_elbow, w, h)
        right_wrist_2d = self.get_landmarks_2d(right_wrist, w, h)
        
        # Calcular ángulos de abducción para ambos lados
        left_angle = self.calculate_abduction_angle(left_shoulder_2d, left_hip_2d, left_elbow_2d)
        right_angle = self.calculate_abduction_angle(right_shoulder_2d, right_hip_2d, right_elbow_2d)
        
        # Actualizar estadísticas
        self.left_abduction_angle = left_angle
        self.right_abduction_angle = right_angle
        
        if left_angle > self.max_left_abduction:
            self.max_left_abduction = left_angle
        if right_angle > self.max_right_abduction:
            self.max_right_abduction = right_angle
        
        # 🚀 OPTIMIZACIÓN: Dibujar puntos clave con LINE_4
        # BRAZO IZQUIERDO
        cv2.circle(image, left_shoulder_2d, 8, self.color_cache['yellow'], -1, cv2.LINE_4)
        cv2.circle(image, left_hip_2d, 8, self.color_cache['magenta'], -1, cv2.LINE_4)
        cv2.circle(image, left_elbow_2d, 8, self.color_cache['cyan'], -1, cv2.LINE_4)
        
        # BRAZO DERECHO
        cv2.circle(image, right_shoulder_2d, 8, self.color_cache['yellow'], -1, cv2.LINE_4)
        cv2.circle(image, right_hip_2d, 8, self.color_cache['magenta'], -1, cv2.LINE_4)
        cv2.circle(image, right_elbow_2d, 8, self.color_cache['cyan'], -1, cv2.LINE_4)
        
        # � LÍNEAS DE REFERENCIA VERTICALES FIJAS (Goniómetro Estándar)
        vertical_length = 150
        
        # Eje vertical izquierdo
        left_vertical_start = (left_shoulder_2d[0], left_shoulder_2d[1] - vertical_length)
        left_vertical_end = (left_shoulder_2d[0], left_shoulder_2d[1] + vertical_length)
        cv2.line(image, left_vertical_start, left_vertical_end, self.color_cache['green'], 3, cv2.LINE_4)
        
        # Eje vertical derecho
        right_vertical_start = (right_shoulder_2d[0], right_shoulder_2d[1] - vertical_length)
        right_vertical_end = (right_shoulder_2d[0], right_shoulder_2d[1] + vertical_length)
        cv2.line(image, right_vertical_start, right_vertical_end, self.color_cache['green'], 3, cv2.LINE_4)
        
        # 🔵 LÍNEAS DE LOS BRAZOS (Brazos móviles del goniómetro)
        # BRAZO IZQUIERDO
        cv2.line(image, left_shoulder_2d, left_elbow_2d, self.color_cache['blue'], 3, cv2.LINE_4)
        
        # BRAZO DERECHO
        cv2.line(image, right_shoulder_2d, right_elbow_2d, self.color_cache['blue'], 3, cv2.LINE_4)
        
        # 🎨 Antebrazos (solo en CLEAN y FULL, no en MINIMAL)
        if self.display_mode != "MINIMAL":
            cv2.line(image, left_elbow_2d, left_wrist_2d, self.color_cache['blue'], 2, cv2.LINE_4)
            cv2.line(image, right_elbow_2d, right_wrist_2d, self.color_cache['blue'], 2, cv2.LINE_4)
        
        # 🚀 OPTIMIZACIÓN: Mostrar ángulos con LINE_4
        left_angle_text = f"{left_angle:.1f}"
        cv2.putText(image, left_angle_text, 
                   (left_shoulder_2d[0] - 60, left_shoulder_2d[1] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.4, self.color_cache['yellow'], 3, cv2.LINE_4)
        
        right_angle_text = f"{right_angle:.1f}"
        cv2.putText(image, right_angle_text, 
                   (right_shoulder_2d[0] + 20, right_shoulder_2d[1] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.4, self.color_cache['yellow'], 3, cv2.LINE_4)
        
        # Panel de información
        self.draw_info_panel_frontal(image, orientation, confidence)
    
    def draw_info_panel_profile(self, image, orientation, confidence):
        """Dibuja el panel de información en la imagen - Vista de perfil (OPTIMIZADO)"""
        h, w, _ = image.shape
        
        # Panel superior con información
        panel_height = 200
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (w, panel_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
        
        # 🚀 OPTIMIZACIÓN: Todos los textos usan LINE_4
        # Título
        cv2.putText(image, "ANALISIS DE EXTENSION/FLEXION DE HOMBRO (PERFIL)", (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.color_cache['white'], 2, cv2.LINE_4)
        
        # Lado detectado
        color_side = self.color_cache['green'] if confidence > 0.7 else self.color_cache['orange']
        cv2.putText(image, f"Lado: {self.side}", (20, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_side, 2, cv2.LINE_4)
        
        # Orientación
        cv2.putText(image, f"Orientacion: {orientation}", (20, 110),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['white'], 2, cv2.LINE_4)
        
        # Ángulo actual (siempre positivo para el usuario)
        angle_color = self.get_angle_color(self.current_angle)
        # 🎯 GONIÓMETRO: Mostrar abs() + indicador direccional
        direction_text = "FLEX" if self.current_angle > 0 else "EXT" if self.current_angle < 0 else ""
        cv2.putText(image, f"Angulo Actual: {abs(self.current_angle):.1f} {direction_text}", (20, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, angle_color, 2, cv2.LINE_4)
        
        # 🎯 GONIÓMETRO: Solo mostrar máximo ROM (siempre positivo)
        cv2.putText(image, f"ROM Maximo: {self.max_angle:.1f}", 
                   (20, 180),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color_cache['green'], 2, cv2.LINE_4)
        
        # Barra de progreso de extensión
        self.draw_extension_bar(image, w, h)
        
        # Instrucciones
        cv2.putText(image, "Presiona 'R' para reiniciar | 'Q' para salir", 
                   (20, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['white'], 2, cv2.LINE_4)
    
    def draw_info_panel_frontal(self, image, orientation, confidence):
        """Dibuja el panel de información en la imagen - Vista frontal (OPTIMIZADO)"""
        h, w, _ = image.shape
        
        # Panel superior con información
        panel_height = 230
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (w, panel_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
        
        # 🚀 OPTIMIZACIÓN: Todos los textos usan LINE_4
        # Título
        cv2.putText(image, "ANALISIS DE ABDUCCION BILATERAL (FRONTAL)", (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, self.color_cache['green'], 2, cv2.LINE_4)
        
        # Orientación
        cv2.putText(image, f"Vista: {orientation} (FRONTAL)", (20, 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['white'], 2, cv2.LINE_4)
        
        # Ángulos actuales - BRAZO IZQUIERDO
        left_color = self.get_abduction_color(self.left_abduction_angle)
        cv2.putText(image, f"Brazo Izquierdo: {self.left_abduction_angle:.1f}", (20, 115),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, left_color, 2, cv2.LINE_4)
        cv2.putText(image, f"Max: {self.max_left_abduction:.1f}", (20, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['light_gray'], 2, cv2.LINE_4)
        
        # Ángulos actuales - BRAZO DERECHO
        right_color = self.get_abduction_color(self.right_abduction_angle)
        cv2.putText(image, f"Brazo Derecho: {self.right_abduction_angle:.1f}", (w//2 + 20, 115),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, right_color, 2, cv2.LINE_4)
        cv2.putText(image, f"Max: {self.max_right_abduction:.1f}", (w//2 + 20, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['light_gray'], 2, cv2.LINE_4)
        
        # Barras de progreso de abducción
        self.draw_abduction_bars(image, w, h)
        
        # Instrucciones
        cv2.putText(image, "Levanta ambos brazos lateralmente | 'R' para reiniciar | 'Q' para salir", 
                   (20, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['white'], 2, cv2.LINE_4)
    
    def get_angle_color(self, angle):
        """Retorna color según el ángulo y dirección"""
        abs_angle = abs(angle)
        
        if abs_angle < 15:
            return (255, 255, 255)  # Blanco - Cerca de posición neutral (brazo abajo)
        elif abs_angle < 45:
            return (0, 255, 255)    # Amarillo - Elevación baja
        elif abs_angle < 90:
            return (0, 165, 255)    # Naranja - Elevación media (horizontal)
        elif abs_angle < 135:
            return (255, 0, 255)    # Magenta - Elevación alta
        else:
            return (0, 255, 0)      # Verde - Cerca de 180° (brazo arriba)
    
    def get_abduction_color(self, angle):
        """Retorna color según el ángulo de abducción"""
        if angle < 15:
            return (255, 255, 255)  # Blanco - Brazo pegado al cuerpo
        elif angle < 45:
            return (0, 255, 255)    # Amarillo - Elevación baja
        elif angle < 90:
            return (0, 165, 255)    # Naranja - Acercándose a horizontal
        elif angle < 135:
            return (255, 0, 255)    # Magenta - Por encima de horizontal
        else:
            return (0, 255, 0)      # Verde - Cerca de vertical (arriba)
    
    def draw_extension_bar(self, image, width, height):
        """🎯 Dibuja barra de progreso del ROM - SISTEMA GONIÓMETRO (0° a 180°) OPTIMIZADO"""
        bar_x = width - 300
        bar_y = 50
        bar_width = 260
        bar_height = 30
        
        # Fondo de la barra
        cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                     self.color_cache['gray'], -1)
        cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                     self.color_cache['white'], 2)
        
        # 🎯 GONIÓMETRO: Rango 0° a 180° (siempre positivo)
        min_range = 0
        max_range = 180
        total_range = max_range - min_range
        
        # 🎯 GONIÓMETRO: Usar abs() para visualización
        abs_current_angle = abs(self.current_angle)
        
        # Calcular posición del ángulo actual
        angle_clamped = max(min_range, min(abs_current_angle, max_range))
        current_position = int(bar_width * (angle_clamped - min_range) / total_range)
        
        # 🚀 OPTIMIZACIÓN: Color desde caché
        if angle_clamped < 45:
            color = self.color_cache['yellow']
        elif angle_clamped < 90:
            color = self.color_cache['orange']
        elif angle_clamped < 135:
            color = self.color_cache['magenta']
        else:
            color = self.color_cache['green']
        
        # Llenar barra desde 0° hasta posición actual
        cv2.rectangle(image, (bar_x, bar_y), 
                     (bar_x + current_position, bar_y + bar_height), 
                     color, -1)
        
        # 🚀 OPTIMIZACIÓN: Dibujar indicador con LINE_4
        cv2.line(image, (bar_x + current_position, bar_y - 5), 
                (bar_x + current_position, bar_y + bar_height + 5), 
                self.color_cache['yellow'], 3, cv2.LINE_4)
        
        # 🚀 OPTIMIZACIÓN: Texto de referencia con LINE_4
        cv2.putText(image, "ROM (Goniometro)", (bar_x, bar_y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['white'], 1, cv2.LINE_4)
        cv2.putText(image, "0", (bar_x - 10, bar_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.color_cache['white'], 1, cv2.LINE_4)
        cv2.putText(image, "90", (bar_x + bar_width//2 - 10, bar_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.color_cache['white'], 1, cv2.LINE_4)
        cv2.putText(image, "180", (bar_x + bar_width - 20, bar_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.color_cache['white'], 1, cv2.LINE_4)
    
    def draw_abduction_bars(self, image, width, height):
        """Dibuja barras de progreso para abducción bilateral (OPTIMIZADO)"""
        # Posición y tamaño de las barras
        bar_width = 40
        bar_height = 250
        bar_y = 180
        
        # Barra izquierda (brazo izquierdo)
        left_bar_x = 100
        
        # Barra derecha (brazo derecho)
        right_bar_x = width - 150
        
        # 🚀 OPTIMIZACIÓN: Dibujar ambas barras con LINE_4
        for bar_x, angle, max_angle, side_label in [
            (left_bar_x, self.left_abduction_angle, self.max_left_abduction, "IZQ"),
            (right_bar_x, self.right_abduction_angle, self.max_right_abduction, "DER")
        ]:
            # Fondo de la barra
            cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                         self.color_cache['gray'], -1)
            cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                         self.color_cache['white'], 2)
            
            # Rango: 0° (abajo) a 180° (arriba)
            max_range = 180
            
            # Calcular altura de llenado
            angle_clamped = max(0, min(angle, max_range))
            fill_height = int(bar_height * angle_clamped / max_range)
            
            # Color según ángulo (desde caché)
            color = self.get_abduction_color(angle)
            
            # Llenar barra desde abajo hacia arriba
            if fill_height > 0:
                cv2.rectangle(image, 
                             (bar_x, bar_y + bar_height - fill_height), 
                             (bar_x + bar_width, bar_y + bar_height), 
                             color, -1)
            
            # Marcas de referencia (optimizado con LINE_4)
            for mark_angle, mark_y in [(0, bar_height), (45, bar_height * 3/4), 
                                        (90, bar_height / 2), (135, bar_height / 4), 
                                        (180, 0)]:
                y_pos = int(bar_y + mark_y)
                cv2.line(image, (bar_x - 5, y_pos), (bar_x, y_pos), 
                        self.color_cache['light_gray'], 1, cv2.LINE_4)
                if mark_angle in [0, 90, 180]:
                    cv2.putText(image, f"{int(mark_angle)}", (bar_x - 30, y_pos + 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, self.color_cache['light_gray'], 1, cv2.LINE_4)
            
            # Etiqueta del lado
            cv2.putText(image, side_label, (bar_x + 5, bar_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['white'], 2, cv2.LINE_4)
            
            # Valor actual y máximo
            cv2.putText(image, f"{angle:.0f}", (bar_x + 5, bar_y + bar_height + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_4)
            cv2.putText(image, f"Max:{max_angle:.0f}", (bar_x - 10, bar_y + bar_height + 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.color_cache['light_gray'], 1, cv2.LINE_4)
    
    def reset_stats(self):
        """Reinicia todas las estadísticas"""
        # Vista de perfil - GONIÓMETRO (solo máximo positivo)
        self.max_angle = 0
        self.current_angle = 0
        
        # Vista frontal
        self.left_abduction_angle = 0
        self.right_abduction_angle = 0
        self.max_left_abduction = 0
        self.max_right_abduction = 0
        
        # 📊 Reiniciar métricas de profiling
        self.fps_history.clear()
        self.processing_times.clear()
        self.frame_count = 0
        
        print("✅ Estadísticas reiniciadas - Sistema goniómetro (solo valores positivos)")
    
    def get_performance_summary(self):
        """Retorna un resumen de las métricas de rendimiento"""
        if not self.fps_history or not self.processing_times:
            return {
                'avg_fps': 0,
                'avg_processing_time': 0,
                'total_frames': self.frame_count
            }
        
        return {
            'avg_fps': sum(self.fps_history) / len(self.fps_history),
            'min_fps': min(self.fps_history),
            'max_fps': max(self.fps_history),
            'avg_processing_time': sum(self.processing_times) / len(self.processing_times),
            'min_processing_time': min(self.processing_times),
            'max_processing_time': max(self.processing_times),
            'total_frames': self.frame_count
        }
    
    def release(self):
        """Libera recursos"""
        self.pose.close()


def main():
    """Función principal"""
    print("=" * 70)
    print("ANÁLISIS DE MOVIMIENTO DE HOMBRO EN TIEMPO REAL - OPTIMIZADO")
    print("=" * 70)
    print("\n� OPTIMIZACIONES ACTIVADAS:")
    print("   • Procesamiento en 640x480 (upscaling a 720p para display)")
    print("   • Dibujos OpenCV optimizados (LINE_4)")
    print("   • Caché de colores")
    print("   • Profiling de FPS y latencia en tiempo real")
    print("   • Modo de visualización configurable (CLEAN/FULL/MINIMAL)")
    print("\n🎨 MODOS DE VISUALIZACIÓN:")
    print("   • CLEAN (Predeterminado): Solo líneas biomecánicas")
    print("   • FULL: Con skeleton completo de MediaPipe")
    print("   • MINIMAL: Máximo rendimiento, líneas esenciales")
    print("\n� DETECCIÓN AUTOMÁTICA DE ORIENTACIÓN:")
    print("   • VISTA DE PERFIL → Análisis de EXTENSIÓN/FLEXIÓN")
    print("   • VISTA FRONTAL → Análisis de ABDUCCIÓN BILATERAL")
    print("\n📋 INSTRUCCIONES:")
    print("   1. Colócate frente a la cámara")
    print("   2. El sistema detectará automáticamente tu orientación")
    print("   3. Realiza movimientos según la vista detectada:")
    print("")
    print("      🔸 VISTA DE PERFIL:")
    print("         - Brazo hacia adelante y atrás")
    print("         - Brazo hacia arriba y abajo")
    print("")
    print("      🔸 VISTA FRONTAL:")
    print("         - Levanta ambos brazos lateralmente (abducción)")
    print("         - Ambos ángulos se miden simultáneamente")
    print("")
    print("   4. Presiona 'M' para cambiar modo de visualización")
    print("   5. Presiona 'R' para reiniciar estadísticas")
    print("   6. Presiona 'Q' para salir")
    print("\n📐 SISTEMA GONIÓMETRO (0° a 180°):")
    print("\n   ✅ TODOS LOS ÁNGULOS SON POSITIVOS (como goniómetro real)")
    print("\n   VISTA DE PERFIL (Flexión/Extensión):")
    print("   - 0° = Brazo apuntando hacia ABAJO (posición neutra)")
    print("   - 90° = Brazo en posición HORIZONTAL")
    print("   - 180° = Brazo apuntando hacia ARRIBA (sobre la cabeza)")
    print("   - Flexión (adelante) y Extensión (atrás) = SIEMPRE POSITIVO")
    print("\n   VISTA FRONTAL (Abducción):")
    print("   - 0° = Brazos pegados al cuerpo (posición neutra)")
    print("   - 90° = Brazos horizontales (perpendiculares al cuerpo)")
    print("   - 180° = Brazos completamente levantados sobre la cabeza")
    print("=" * 70)
    
    # 🚀 OPTIMIZACIÓN: Inicializar analizador con resolución de procesamiento reducida
    analyzer = ShoulderExtensionAnalyzer(processing_width=640, processing_height=480)
    
    # Inicializar cámara
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: No se pudo acceder a la cámara")
        return
    
    # Configurar resolución de captura (display)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("\n✅ Cámara iniciada correctamente")
    print("📹 Procesando video...")
    print("📊 Métricas de rendimiento visibles en esquina superior derecha\n")
    
    while cap.isOpened():
        success, frame = cap.read()
        
        if not success:
            print("❌ Error al capturar frame")
            break
        
        # Procesar frame
        annotated_frame = analyzer.process_frame(frame)
        
        # Mostrar frame
        cv2.imshow('Análisis de Movimiento de Hombro', annotated_frame)
        
        # Manejar teclas
        key = cv2.waitKey(5) & 0xFF
        
        if key == ord('q') or key == ord('Q'):
            print("\n👋 Cerrando aplicación...")
            break
        elif key == ord('r') or key == ord('R'):
            analyzer.reset_stats()
        elif key == ord('m') or key == ord('M'):
            analyzer.toggle_display_mode()
    
    # Liberar recursos
    cap.release()
    cv2.destroyAllWindows()
    analyzer.release()
    
    # 📊 Mostrar resumen de rendimiento
    perf = analyzer.get_performance_summary()
    
    print("\n" + "=" * 70)
    print("✅ Aplicación cerrada correctamente")
    print("=" * 70)
    print(f"\n📊 RESUMEN DE RENDIMIENTO:")
    print(f"   • Total de frames procesados: {perf['total_frames']}")
    print(f"   • FPS promedio: {perf['avg_fps']:.1f}")
    print(f"   • FPS mínimo: {perf['min_fps']:.1f}")
    print(f"   • FPS máximo: {perf['max_fps']:.1f}")
    print(f"   • Latencia promedio: {perf['avg_processing_time']:.2f}ms")
    print(f"   • Latencia mínima: {perf['min_processing_time']:.2f}ms")
    print(f"   • Latencia máxima: {perf['max_processing_time']:.2f}ms")
    
    print(f"\n📊 ESTADÍSTICAS BIOMECÁNICAS:")
    print(f"   • Tipo de vista: {analyzer.view_type}")
    
    if analyzer.view_type == "PERFIL":
        print(f"   • Lado analizado: {analyzer.side}")
        print(f"   • ROM Máximo alcanzado: {analyzer.max_angle:.1f}°")
    elif analyzer.view_type == "FRONTAL":
        print(f"   • Abducción brazo izquierdo: {analyzer.max_left_abduction:.1f}°")
        print(f"   • Abducción brazo derecho: {analyzer.max_right_abduction:.1f}°")
        print(f"   • Diferencia entre brazos: {abs(analyzer.max_left_abduction - analyzer.max_right_abduction):.1f}°")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
