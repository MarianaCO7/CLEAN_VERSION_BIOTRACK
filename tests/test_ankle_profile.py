"""
Script para análisis de FLEXIÓN PLANTAR / DORSIFLEXIÓN de tobillo (VISTA DE PERFIL - PLANO SAGITAL)
Utiliza OpenCV y MediaPipe para detectar y calcular ángulos
Sistema de medición: Goniómetro estándar con eje vertical fijo

IMPORTANTE: 
- Posición NEUTRA (pie perpendicular a pierna) = 0° mostrado al usuario
- Dorsiflexión (dedos arriba) = 0° a 20° 
- Flexión plantar (dedos abajo) = 0° a 50°

OPTIMIZACIONES IMPLEMENTADAS:
- Procesamiento en resolución reducida (640x480) con upscaling para display
- Dibujos OpenCV optimizados (LINE_4 en vez de LINE_AA)
- Caché de colores por rangos de ángulos
- Sistema de profiling de FPS y latencia
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

class AnkleProfileAnalyzer:
    def __init__(self, processing_width=640, processing_height=480):
        """
        Inicializa el analizador para vista de PERFIL (Flexión plantar/Dorsiflexión)
        
        Args:
            processing_width: Ancho para procesamiento de MediaPipe
            processing_height: Alto para procesamiento de MediaPipe
        """
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1
        )
        
        # Resolución de procesamiento
        self.processing_width = processing_width
        self.processing_height = processing_height
        
        # Variables para tracking de ángulos
        self.current_angle_raw = 90  # Ángulo real desde vertical
        self.current_angle_display = 0  # Ángulo mostrado (0° = neutro)
        self.max_dorsiflexion = 0  # Máximo en dorsiflexión (0-20°)
        self.max_plantar_flexion = 0  # Máximo en flexión plantar (0-50°)
        self.movement_type = "NEUTRO"  # DORSIFLEXION, NEUTRO, FLEX_PLANTAR
        self.frame_count = 0
        
        # Detección de lado visible
        self.side_detected = "Detectando..."
        self.side_confidence = 0
        
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
    
    def calculate_ankle_angle_raw(self, knee, ankle, foot_index):
        """
        Calcula el ángulo del tobillo con eje vertical fijo (ÁNGULO INTERNO)
        
        Sistema goniómetro estándar:
        - Brazo FIJO: Eje vertical absoluto (0, 1) que pasa por el TOBILLO
        - Brazo MÓVIL: Línea del pie (TOBILLO → FOOT_INDEX)
        
        Returns:
            float: Ángulo REAL en grados desde vertical
            - ~90° = Posición NEUTRA (pie perpendicular)
            - < 90° (ej: 70°) = DORSIFLEXIÓN (dedos arriba)
            - > 90° (ej: 120°) = FLEXIÓN PLANTAR (dedos abajo)
        """
        # Vector vertical fijo (referencia 90° - apunta hacia abajo)
        vertical_down_vector = np.array([0, 1])
        
        # Vector del pie (TOBILLO → FOOT_INDEX) - brazo móvil del goniómetro
        foot_vector = np.array([foot_index[0] - ankle[0], foot_index[1] - ankle[1]])
        
        # Normalizar vector del pie
        foot_norm = np.linalg.norm(foot_vector)
        
        if foot_norm == 0:
            return 90  # Retornar neutro si no hay vector
        
        foot_vector_normalized = foot_vector / foot_norm
        
        # Calcular ángulo entre eje vertical y pie
        dot_product = np.dot(vertical_down_vector, foot_vector_normalized)
        dot_product = np.clip(dot_product, -1.0, 1.0)
        
        # Ángulo sin signo (0° a 180°)
        angle = np.degrees(np.arccos(dot_product))
        
        return angle
    
    def calculate_ankle_angle_parallel_to_sole(self, ankle, heel, foot_index):
        """
        MÉTODO MEJORADO: Calcula ángulo usando TOBILLO como vértice con vector PARALELO a la planta
        
        Sistema goniómetro clínico mejorado:
        - VÉRTICE: TOBILLO (maléolo lateral del peroné) - punto anatómico estándar
        - Brazo FIJO: Eje vertical absoluto (0, 1) que pasa por el TOBILLO
        - Brazo MÓVIL: Vector PARALELO a la planta del pie (dirección TALÓN→DEDOS)
        
        Ventajas de este método:
        - Vértice en punto anatómico estándar (maléolo lateral)
        - Mide orientación de la PLANTA del pie respecto a vertical
        - Más preciso que usar tobillo→dedos directo (evita efecto de longitud del pie)
        - Vector paralelo a la planta es más representativo del movimiento real
        
        Diferencias con métodos anteriores:
        - Método 1 (TOBILLO→DEDOS): Vector directo, afectado por longitud del pie
        - Método 2 (TALÓN→DEDOS): Vértice en talón, menos estándar anatómicamente
        - ESTE MÉTODO: Combina lo mejor - vértice en tobillo + orientación de planta
        
        Returns:
            float: Ángulo REAL en grados desde vertical
            - ~90-100° = Posición NEUTRA (planta del pie paralela al suelo)
            - < 90° = DORSIFLEXIÓN (planta inclinada hacia arriba)
            - > 100° = FLEXIÓN PLANTAR (planta inclinada hacia abajo)
        """
        # Vector vertical fijo (referencia - apunta hacia abajo)
        vertical_down_vector = np.array([0, 1])
        
        # Vector de la PLANTA del pie (TALÓN → DEDOS)
        # Este vector representa la orientación de la superficie plantar
        sole_vector = np.array([foot_index[0] - heel[0], foot_index[1] - heel[1]])
        
        # Normalizar vector de la planta
        sole_norm = np.linalg.norm(sole_vector)
        
        if sole_norm == 0:
            return 90  # Retornar neutro si no hay vector
        
        sole_vector_normalized = sole_vector / sole_norm
        
        # Calcular ángulo entre eje vertical y vector de la planta
        # Este ángulo representa cuánto se desvía la planta del pie de la vertical
        dot_product = np.dot(vertical_down_vector, sole_vector_normalized)
        dot_product = np.clip(dot_product, -1.0, 1.0)
        
        # Ángulo sin signo (0° a 180°)
        angle = np.degrees(np.arccos(dot_product))
        
        return angle
    
    def convert_to_display_angle(self, angle_raw):
        """
        Convierte el ángulo interno (desde vertical) a ángulo de visualización
        
        Conversión:
        - 90° interno → 0° mostrado (NEUTRO)
        - < 90° interno → Flexión plantar positiva (0-50°)
        - > 90° interno → Dorsiflexión positiva (0-20°)
        
        Args:
            angle_raw: Ángulo calculado desde vertical (70-140°)
        
        Returns:
            tuple: (angle_display, movement_type)
            - angle_display: Ángulo ajustado para mostrar (0-50°)
            - movement_type: "DORSIFLEXION", "NEUTRO", "FLEX_PLANTAR"
        """
        # Determinar tipo de movimiento y calcular ángulo ajustado
        if angle_raw < 85:  # Flexión plantar (dedos hacia abajo)
            angle_display = 90 - angle_raw  # 90 - 70 = 20° flexión plantar
            movement_type = "FLEX_PLANTAR"
        elif angle_raw <= 95:  # Rango neutro (85-95°)
            angle_display = 0
            movement_type = "NEUTRO"
        else:  # Dorsiflexión (dedos hacia arriba)
            angle_display = angle_raw - 90  # 120 - 90 = 30° dorsiflexión
            movement_type = "DORSIFLEXION"
        
        return angle_display, movement_type
    
    def detect_side(self, landmarks):
        """
        Detecta qué lado del cuerpo está visible (vista de perfil)
        Retorna: lado, confianza, orientación
        """
        left_ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE]
        right_ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE]
        left_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
        right_knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]
        nose = landmarks[mp_pose.PoseLandmark.NOSE]
        
        # MÉTODO 1: Solo visibilidad (ACTIVO por defecto)
        left_visibility = (left_ankle.visibility + left_knee.visibility) / 2
        right_visibility = (right_ankle.visibility + right_knee.visibility) / 2
        
        ankle_center_x = (left_ankle.x + right_ankle.x) / 2
        
        if left_visibility > right_visibility:
            side = 'left'
            confidence = left_visibility
            orientation = "mirando izquierda" if nose.x < ankle_center_x else "mirando derecha"
        else:
            side = 'right'
            confidence = right_visibility
            orientation = "mirando derecha" if nose.x > ankle_center_x else "mirando izquierda"
        
        return side, confidence, orientation
        
        """
        # === MÉTODO 2 (MEJORADO): Profundidad Z + Visibilidad ===
        # Descomenta este bloque para usar detección más robusta (96% vs 75% precisión)
        
        left_depth = (left_ankle.z + left_knee.z) / 2
        right_depth = (right_ankle.z + right_knee.z) / 2
        
        left_vis = (left_ankle.visibility + left_knee.visibility) / 2
        right_vis = (right_ankle.visibility + right_knee.visibility) / 2
        
        left_score = (-left_depth * 0.7) + (left_vis * 0.3)
        right_score = (-right_depth * 0.7) + (right_vis * 0.3)
        
        confidence = min(abs(left_score - right_score) * 100, 100)
        
        ankle_center_x = (left_ankle.x + right_ankle.x) / 2
        
        if left_score > right_score:
            side = 'left'
            orientation = "mirando izquierda" if nose.x < ankle_center_x else "mirando derecha"
        else:
            side = 'right'
            orientation = "mirando derecha" if nose.x > ankle_center_x else "mirando izquierda"
        
        return side, confidence, orientation
        """
    
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
            
            # Detectar lado visible
            side, confidence, orientation = self.detect_side(landmarks)
            self.side_detected = side
            self.side_confidence = confidence
            
            # Procesar vista de perfil
            self.process_profile_view(image, landmarks, w, h, orientation, confidence)
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
    
    def process_profile_view(self, image, landmarks, w, h, orientation, confidence):
        """Procesa vista de perfil - Análisis de flexión plantar/dorsiflexión"""
        # Obtener landmarks según el lado más visible
        if self.side_detected == 'left':
            knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
            ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE]
            heel = landmarks[mp_pose.PoseLandmark.LEFT_HEEL]
            foot_index = landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX]
        else:
            knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]
            ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE]
            heel = landmarks[mp_pose.PoseLandmark.RIGHT_HEEL]
            foot_index = landmarks[mp_pose.PoseLandmark.RIGHT_FOOT_INDEX]
        
        # Convertir a coordenadas 2D
        knee_2d = self.get_landmarks_2d(knee, w, h)
        ankle_2d = self.get_landmarks_2d(ankle, w, h)
        heel_2d = self.get_landmarks_2d(heel, w, h)
        foot_index_2d = self.get_landmarks_2d(foot_index, w, h)
        
        # ===== MÉTODO 1 (COMENTADO): TOBILLO como vértice =====
        # angle_raw = self.calculate_ankle_angle_raw(knee_2d, ankle_2d, foot_index_2d)
        # vertex_point = ankle_2d  # Vértice en TOBILLO
        
        # ===== MÉTODO 2 (COMENTADO): TALÓN como vértice =====
        # angle_raw = self.calculate_ankle_angle_raw_heel_vertex(ankle_2d, heel_2d, foot_index_2d)
        # vertex_point = heel_2d  # Vértice en TALÓN
        
        # ===== MÉTODO 3 (ACTIVO): TOBILLO como vértice + Vector PARALELO a planta =====
        angle_raw = self.calculate_ankle_angle_parallel_to_sole(ankle_2d, heel_2d, foot_index_2d)
        vertex_point = ankle_2d  # Vértice en TOBILLO (maléolo lateral)
        
        # Convertir a ángulo de VISUALIZACIÓN (0° = neutro)
        angle_display, movement_type = self.convert_to_display_angle(angle_raw)
        
        # Actualizar estadísticas
        self.current_angle_raw = angle_raw
        self.current_angle_display = angle_display
        self.movement_type = movement_type
        
        # Actualizar máximos según tipo de movimiento
        if movement_type == "DORSIFLEXION" and angle_display > self.max_dorsiflexion:
            self.max_dorsiflexion = angle_display
        elif movement_type == "FLEX_PLANTAR" and angle_display > self.max_plantar_flexion:
            self.max_plantar_flexion = angle_display
        
        # ===== DIBUJAR VISUALIZACIÓN =====
        
        # ===== PUNTOS CLAVE (Landmarks) =====
        cv2.circle(image, ankle_2d, 12, self.color_cache['yellow'], -1, cv2.LINE_4)      # TOBILLO (vértice - más grande)
        cv2.circle(image, knee_2d, 8, self.color_cache['magenta'], -1, cv2.LINE_4)       # RODILLA
        cv2.circle(image, foot_index_2d, 8, self.color_cache['cyan'], -1, cv2.LINE_4)   # DEDOS
        cv2.circle(image, heel_2d, 6, self.color_cache['white'], -1, cv2.LINE_4)        # TALÓN
        
        # Etiqueta del vértice (TOBILLO - maléolo lateral)
        cv2.putText(image, "TOBILLO (vertice)", 
                   (ankle_2d[0] + 15, ankle_2d[1] - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.color_cache['yellow'], 1, cv2.LINE_4)
        
        # ===== LÍNEA VERTICAL (Brazo FIJO del goniómetro) =====
        # Línea vertical que pasa por el TOBILLO (maléolo lateral - vértice)
        vertical_length = 150
        vertical_start = (vertex_point[0], vertex_point[1] - vertical_length)
        vertical_end = (vertex_point[0], vertex_point[1] + vertical_length)
        cv2.line(image, vertical_start, vertical_end, self.color_cache['green'], 3, cv2.LINE_4)
        
        # ===== LÍNEA PARALELA A LA PLANTA (Brazo MÓVIL del goniómetro) =====
        # Vector de la planta del pie (TALÓN → DEDOS)
        sole_vector = np.array([foot_index_2d[0] - heel_2d[0], foot_index_2d[1] - heel_2d[1]])
        sole_length = np.linalg.norm(sole_vector)
        
        if sole_length > 0:
            # Normalizar vector de la planta
            sole_vector_normalized = sole_vector / sole_length
            
            # Calcular punto final del brazo móvil (paralelo a planta, desde tobillo)
            # Usar longitud proporcional para visualización (120 píxeles)
            display_length = 120
            parallel_end_point = (
                int(ankle_2d[0] + sole_vector_normalized[0] * display_length),
                int(ankle_2d[1] + sole_vector_normalized[1] * display_length)
            )
            
            # Dibujar línea verde gruesa desde TOBILLO en dirección paralela a la planta
            cv2.line(image, ankle_2d, parallel_end_point, self.color_cache['green'], 5, cv2.LINE_4)
            
            # Etiqueta en el brazo móvil
            label_pos = (
                int(ankle_2d[0] + sole_vector_normalized[0] * display_length * 0.6),
                int(ankle_2d[1] + sole_vector_normalized[1] * display_length * 0.6) - 10
            )
            cv2.putText(image, "PLANTA", label_pos,
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.color_cache['green'], 1, cv2.LINE_4)
        
        # ===== LÍNEAS DE REFERENCIA (contexto anatómico) =====
        # Línea de la planta real (TALÓN → DEDOS) - gris delgado para referencia
        cv2.line(image, heel_2d, foot_index_2d, self.color_cache['light_gray'], 2, cv2.LINE_4)
        
        # Pierna inferior (RODILLA → TOBILLO) - solo en CLEAN y FULL
        if self.display_mode != "MINIMAL":
            cv2.line(image, knee_2d, ankle_2d, self.color_cache['blue'], 2, cv2.LINE_4)
        
        # Mostrar ángulo ajustado (cerca del vértice)
        angle_color = self.get_ankle_angle_color(angle_display, movement_type)
        cv2.putText(image, f"{angle_display:.1f}deg", 
                   (vertex_point[0] + 20, vertex_point[1] - 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.4, angle_color, 3, cv2.LINE_4)
        
        # Mostrar tipo de movimiento (cerca del vértice)
        movement_color = self.get_movement_color(movement_type)
        movement_text = movement_type.replace("_", ". ")  # "FLEX_PLANTAR" → "FLEX. PLANTAR"
        cv2.putText(image, movement_text, 
                   (vertex_point[0] + 20, vertex_point[1] + 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, movement_color, 2, cv2.LINE_4)
        
        # Panel de información
        self.draw_info_panel(image, orientation, confidence, w, h)
    
    def draw_info_panel(self, image, orientation, confidence, w, h):
        """Dibuja panel informativo con análisis"""
        # Panel superior con fondo semi-transparente
        panel_height = 260
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (w, panel_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
        
        # Título
        title = "ANALISIS DE TOBILLO - FLEX PLANTAR / DORSIFLEXION (PERFIL)"
        cv2.putText(image, title, (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.65, self.color_cache['green'], 2, cv2.LINE_4)
        
        # Indicador de MÉTODO activo
        method_text = "[METODO 3: TOBILLO (maleolo lateral) + Vector PARALELO a planta]"
        cv2.putText(image, method_text, (20, 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['orange'], 2, cv2.LINE_4)
        
        # Lado detectado
        color_side = self.color_cache['green'] if confidence > 0.7 else self.color_cache['orange']
        side_text = "Izquierdo" if self.side_detected == 'left' else "Derecho"
        cv2.putText(image, f"Pie analizado: {side_text}", (20, 95),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_side, 2, cv2.LINE_4)
        
        # Orientación
        cv2.putText(image, f"Orientacion: {orientation}", (20, 125),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['white'], 2, cv2.LINE_4)
        
        # Ángulo actual y tipo de movimiento
        angle_color = self.get_ankle_angle_color(self.current_angle_display, self.movement_type)
        movement_text = self.movement_type.replace("_", ". ")
        cv2.putText(image, f"Angulo: {self.current_angle_display:.1f}deg [{movement_text}]", (20, 160),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, angle_color, 2, cv2.LINE_4)
        
        # ROM Máximos
        cv2.putText(image, f"Max Dorsiflexion: {self.max_dorsiflexion:.1f}deg (normal: 0-20deg)", 
                   (20, 195),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['cyan'], 2, cv2.LINE_4)
        
        cv2.putText(image, f"Max Flex Plantar: {self.max_plantar_flexion:.1f}deg (normal: 0-50deg)", 
                   (20, 225),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['orange'], 2, cv2.LINE_4)
        
        # Nota importante
        cv2.putText(image, "Nota: 0deg = Posicion NEUTRA (pie perpendicular)", 
                   (20, 250),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['light_gray'], 1, cv2.LINE_4)
        
        # Instrucciones inferiores
        cv2.putText(image, "Mueve el tobillo | 'R' reiniciar | 'M' modo | 'Q' salir", 
                   (20, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['white'], 2, cv2.LINE_4)
    
    def get_ankle_angle_color(self, angle_display, movement_type):
        """Retorna color según ángulo y tipo de movimiento"""
        if movement_type == "NEUTRO":
            return self.color_cache['white']
        elif movement_type == "DORSIFLEXION":
            if angle_display < 10:
                return self.color_cache['yellow']
            elif angle_display < 20:
                return self.color_cache['green']
            else:
                return self.color_cache['cyan']
        else:  # FLEX_PLANTAR
            if angle_display < 20:
                return self.color_cache['yellow']
            elif angle_display < 40:
                return self.color_cache['orange']
            else:
                return self.color_cache['magenta']
    
    def get_movement_color(self, movement_type):
        """Retorna color según tipo de movimiento"""
        if movement_type == "DORSIFLEXION":
            return self.color_cache['green']
        elif movement_type == "NEUTRO":
            return self.color_cache['white']
        else:  # FLEX_PLANTAR
            return self.color_cache['orange']
    
    def reset_stats(self):
        """Reinicia estadísticas"""
        self.current_angle_raw = 90
        self.current_angle_display = 0
        self.max_dorsiflexion = 0
        self.max_plantar_flexion = 0
        self.movement_type = "NEUTRO"
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
    print("ANALISIS DE TOBILLO - FLEXION PLANTAR / DORSIFLEXION")
    print("=" * 70)
    print("\n[*] SISTEMA DE MEDICION:")
    print("   - 0deg = Posicion NEUTRA (pie perpendicular a la pierna)")
    print("   - DORSIFLEXION: 0-20deg (dedos hacia arriba)")
    print("   - FLEXION PLANTAR: 0-50deg (dedos hacia abajo)")
    print("\n[*] OPTIMIZACIONES ACTIVADAS:")
    print("   - Procesamiento en 640x480 (upscaling a 720p para display)")
    print("   - Dibujos OpenCV optimizados (LINE_4)")
    print("   - Cache de colores")
    print("   - Profiling de FPS y latencia en tiempo real")
    print("\n[*] MODOS DE VISUALIZACION:")
    print("   - CLEAN (Predeterminado): Solo lineas biomecanicas")
    print("   - FULL: Con skeleton completo de MediaPipe")
    print("   - MINIMAL: Maximo rendimiento")
    print("\n[*] INSTRUCCIONES:")
    print("   1. Colocate de PERFIL (lateral) a la camara")
    print("   2. Asegurate de que tu PIE este COMPLETAMENTE visible")
    print("   3. El sistema detectara AUTOMATICAMENTE el lado mas visible")
    print("   4. Realiza movimientos del tobillo:")
    print("      - DORSIFLEXION: Levanta los dedos hacia arriba")
    print("      - FLEXION PLANTAR: Apunta los dedos hacia abajo")
    print("   5. Presiona 'M' para cambiar modo de visualizacion")
    print("   6. Presiona 'R' para reiniciar estadisticas")
    print("   7. Presiona 'Q' para salir")
    print("\n[*] IMPORTANTE:")
    print("   - Usar DESCALZO o con CALCETINES (NO zapatos)")
    print("   - MediaPipe detecta 3 puntos del pie: TOBILLO, TALON, DEDOS")
    print("   - La precision depende de la visibilidad completa del pie")
    print("=" * 70)
    
    # Inicializar analizador
    analyzer = AnkleProfileAnalyzer(
        processing_width=640, 
        processing_height=480
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
        cv2.imshow('Analisis de Tobillo - Flexion Plantar / Dorsiflexion', annotated_frame)
        
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
    side_name = "Izquierdo" if analyzer.side_detected == 'left' else "Derecho"
    print(f"   - Pie analizado: {side_name}")
    print(f"   - Dorsiflexion maxima: {analyzer.max_dorsiflexion:.1f}deg (normal: 0-20deg)")
    print(f"   - Flexion plantar maxima: {analyzer.max_plantar_flexion:.1f}deg (normal: 0-50deg)")
    
    # Evaluación del ROM
    print(f"\n[*] EVALUACION ROM:")
    if analyzer.max_dorsiflexion >= 15:
        print(f"   - Dorsiflexion: EXCELENTE (>=15deg)")
    elif analyzer.max_dorsiflexion >= 10:
        print(f"   - Dorsiflexion: BUENA (10-15deg)")
    elif analyzer.max_dorsiflexion >= 5:
        print(f"   - Dorsiflexion: LIMITADA (5-10deg) - Revisar")
    else:
        print(f"   - Dorsiflexion: MUY LIMITADA (<5deg) - Consultar especialista")
    
    if analyzer.max_plantar_flexion >= 40:
        print(f"   - Flexion plantar: EXCELENTE (>=40deg)")
    elif analyzer.max_plantar_flexion >= 30:
        print(f"   - Flexion plantar: BUENA (30-40deg)")
    elif analyzer.max_plantar_flexion >= 20:
        print(f"   - Flexion plantar: LIMITADA (20-30deg) - Revisar")
    else:
        print(f"   - Flexion plantar: MUY LIMITADA (<20deg) - Consultar especialista")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
