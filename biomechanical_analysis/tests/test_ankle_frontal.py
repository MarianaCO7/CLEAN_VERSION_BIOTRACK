"""
=================================================================================
BIOTRACK - ANÁLISIS BIOMECÁNICO DE TOBILLO (Vista FRONTAL)
=================================================================================
Archivo: test_ankle_frontal.py
Articulación: TOBILLO
Plano: FRONTAL/CORONAL
Movimientos: INVERSIÓN (medial) del pie

Sistema de Medición (Goniómetro Clínico con VÉRTICE en TOBILLO):
- VÉRTICE: TOBILLO (punto donde convergen los brazos del goniómetro)
- Brazo FIJO: Eje vertical (0°) que pasa por el TOBILLO (hacia abajo)
- Brazo MÓVIL: Línea desde TOBILLO hacia DEDOS
- Referencia: 0° = Posición NEUTRA (pie alineado verticalmente)

Configuración:
- Vista: FRONTAL (cámara de frente al paciente)
- Selección manual del pie: LEFT/RIGHT (usuario elige antes de iniciar)
- Método detección lado: NO APLICA (usuario selecciona directamente)

Medición Clínica:
- 0° = Posición NEUTRA (vertical perfecta)
- 5-15° = INVERSIÓN leve
- 15-30° = INVERSIÓN moderada
- 30-35° = INVERSIÓN alta (rango normal máximo)
- >35° = INVERSIÓN excesiva

Landmarks MediaPipe utilizados:
- KNEE (rodilla) - Contexto visual
- ANKLE (tobillo) - VÉRTICE del goniómetro (punto de medición)
- HEEL (talón) - Contexto anatómico
- FOOT_INDEX (dedos) - Punto final del brazo móvil

NOTA: Este sistema usa el TOBILLO como vértice del goniómetro,
donde el eje vertical de referencia y el brazo móvil (TOBILLO→DEDOS) convergen.
Se mide el ángulo entre la vertical y la línea que va del tobillo a los dedos.

=================================================================================
"""

import cv2
import mediapipe as mp
import numpy as np
import time
from typing import Tuple, Optional, Dict
from collections import deque

# ======================== CONFIGURACIÓN MEDIAPIPE ========================
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# Optimización de renderizado
DRAWING_SPEC = mp_drawing.DrawingSpec(thickness=1, circle_radius=2)
LINE_STYLE = cv2.LINE_4

# ======================== LANDMARKS DEL TOBILLO (FRONTAL) ========================
"""
Sistema de medición de INVERSIÓN en vista frontal (Goniómetro con VÉRTICE en TOBILLO):

Configuración del goniómetro:
    
    KNEE (rodilla) ← Referencia visual
        │
        │ ← Línea de contexto (RODILLA → TOBILLO)
        │
    ANKLE (tobillo) ← VÉRTICE del goniómetro
        │
        │  ← Brazo MÓVIL (TOBILLO → DEDOS) - medido
        │  ← Eje vertical fijo (0° = referencia neutra)
        │
    HEEL (talón) ← Contexto anatómico
        │
        ↓
    FOOT_INDEX (dedos) ← Punto final del brazo móvil

Medición:
- El vértice del goniómetro se coloca en el TOBILLO
- El brazo fijo es una línea vertical que pasa por el tobillo (0° = neutro)
- El brazo móvil va desde el TOBILLO hacia los DEDOS
- El ángulo se mide entre estos dos brazos

Cuando hay INVERSIÓN, el pie se inclina hacia medial/interno,
haciendo que el brazo móvil (TOBILLO→DEDOS) se desvíe de la vertical.

IMPORTANTE: Este sistema usa TOBILLO como vértice para medir la orientación
completa del pie respecto a la vertical, desde el punto de articulación.
"""

LANDMARKS = {
    'RIGHT': {
        'KNEE': mp_pose.PoseLandmark.RIGHT_KNEE,
        'ANKLE': mp_pose.PoseLandmark.RIGHT_ANKLE,
        'HEEL': mp_pose.PoseLandmark.RIGHT_HEEL,
        'FOOT_INDEX': mp_pose.PoseLandmark.RIGHT_FOOT_INDEX
    },
    'LEFT': {
        'KNEE': mp_pose.PoseLandmark.LEFT_KNEE,
        'ANKLE': mp_pose.PoseLandmark.LEFT_ANKLE,
        'HEEL': mp_pose.PoseLandmark.LEFT_HEEL,
        'FOOT_INDEX': mp_pose.PoseLandmark.LEFT_FOOT_INDEX
    }
}

# ======================== CONFIGURACIÓN DE CÁMARA ========================
# NOTA: Ahora se usa configuración simple como en test_ankle_profile.py
# cap = cv2.VideoCapture(0)
# cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
# cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

"""
# Configuración anterior (comentada):
CAMERA_CONFIG = {
    'id': 0,
    'width': 1280,
    'height': 720,
    'fps': 30,
    'backend': cv2.CAP_DSHOW
}
"""

PROCESSING_SIZE = (640, 480)

# ======================== RANGOS DE MOVIMIENTO (ROM) ========================
"""
Estándares AAOS/AO para INVERSIÓN del tobillo:
- Inversión: 0-35° (desde posición neutra)

NOTA: Valores normales pueden variar entre fuentes (AAOS, AO, etc.)
y también dependen de la flexibilidad individual.
"""
ROM_INVERSION = {
    'MIN': 0,      # Neutro
    'MAX': 35,     # Máxima inversión normal
    'TARGET': 30   # Objetivo terapéutico típico
}

# Umbrales para clasificación de movimiento
THRESHOLD_NEUTRAL = 5  # ±5° se considera neutro


# ======================== CONFIGURACIÓN DE VISUALIZACIÓN ========================
COLORS = {
    # Colores por rango de ángulo (INVERSIÓN)
    'ANGLE_MINIMAL': (100, 100, 100),      # Gris - neutro (0-5°)
    'ANGLE_LOW': (0, 255, 255),            # Amarillo - inversión leve (5-15°)
    'ANGLE_MID': (0, 165, 255),            # Naranja - inversión moderada (15-25°)
    'ANGLE_HIGH': (0, 100, 255),           # Naranja oscuro - inversión alta (25-35°)
    'ANGLE_EXCESSIVE': (0, 0, 255),        # Rojo - inversión excesiva (>35°)
    
    # Colores de landmarks
    'LANDMARK_ACTIVE': (0, 255, 0),        # Verde - landmark visible
    'LANDMARK_INACTIVE': (128, 128, 128),  # Gris - landmark oculto
    
    # Colores de líneas
    'LINE_SEGMENT': (255, 255, 255),       # Blanco - segmentos del ángulo
    
    # Colores de texto
    'TEXT_PRIMARY': (255, 255, 255),       # Blanco
    'TEXT_WARNING': (0, 165, 255),         # Naranja
    'TEXT_ERROR': (0, 0, 255),             # Rojo
    'TEXT_SUCCESS': (0, 255, 0),           # Verde
    
    # Fondos de texto
    'BG_DARK': (0, 0, 0),
    'BG_SEMI': (50, 50, 50)
}

# Modos de visualización
DISPLAY_MODES = {
    'FULL': {
        'show_skeleton': True,
        'show_angle_arc': True,
        'show_measurements': True,
        'show_rom_bar': True,
        'show_stats': True
    },
    'CLEAN': {
        'show_skeleton': True,
        'show_angle_arc': False,
        'show_measurements': True,
        'show_rom_bar': True,
        'show_stats': False
    },
    'MINIMAL': {
        'show_skeleton': False,
        'show_angle_arc': False,
        'show_measurements': True,
        'show_rom_bar': False,
        'show_stats': False
    }
}

CURRENT_DISPLAY_MODE = 'CLEAN'


# ======================== CLASE PRINCIPAL ========================
class AnkleFrontalAnalyzer:
    """Analizador de inversión del tobillo en vista frontal"""
    
    def __init__(self, selected_foot: str):
        """
        Inicializa el analizador
        
        Args:
            selected_foot: 'LEFT' o 'RIGHT' - pie seleccionado manualmente
        """
        self.selected_foot = selected_foot.upper()
        
        # Configuración MediaPipe
        self.pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            enable_segmentation=False,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        
        # Estado del análisis
        self.current_angle = 0.0
        self.current_clinical_angle = 0.0
        self.movement_type = "NEUTRO"
        
        # ROM tracking
        self.rom_inversion = {
            'min': float('inf'),
            'max': 0.0,
            'current': 0.0
        }
        
        # Histórico de ángulos (para suavizado)
        self.angle_history = deque(maxlen=5)
        
        # Estadísticas de sesión
        self.stats = {
            'frames_analyzed': 0,
            'frames_with_detection': 0,
            'max_inversion': 0.0,
            'session_start': time.time()
        }
        
        # Cache de colores
        self._color_cache = {}
    
    def calculate_ankle_angle(self, knee_pos: np.ndarray, ankle_pos: np.ndarray, 
                             heel_pos: np.ndarray, foot_index_pos: np.ndarray) -> Optional[float]:
        """
        Calcula el ángulo de INVERSIÓN del tobillo en vista frontal
        
        Sistema de medición (goniómetro con VÉRTICE en TOBILLO):
        - VÉRTICE: TOBILLO (ankle) - punto donde convergen los brazos del goniómetro
        - Brazo FIJO: Eje vertical (0°) que pasa por el TOBILLO (hacia abajo)
        - Brazo MÓVIL: Línea desde TOBILLO hacia DEDOS (FOOT_INDEX)
        
        Cuando hay inversión, el pie se inclina medialmente y el ángulo
        entre la vertical y la línea TOBILLO→DEDOS aumenta.
        
        Args:
            knee_pos: Posición de la rodilla [x, y] (contexto visual)
            ankle_pos: Posición del tobillo (VÉRTICE) [x, y]
            heel_pos: Posición del talón [x, y] (contexto visual)
            foot_index_pos: Posición de los dedos [x, y]
        
        Returns:
            Ángulo en grados (0° = vertical perfecto/neutro) o None si no se puede calcular
        """
        # Vector vertical fijo (referencia 0° - apunta hacia ABAJO)
        # En coordenadas de imagen: Y positivo = hacia abajo
        vertical_down_vector = np.array([0, 1])
        
        # Vector del pie desde TOBILLO hacia DEDOS (brazo móvil del goniómetro)
        foot_vector = np.array([foot_index_pos[0] - ankle_pos[0], 
                                foot_index_pos[1] - ankle_pos[1]])
        
        # Normalizar vector del pie
        foot_norm = np.linalg.norm(foot_vector)
        
        if foot_norm < 0.01:
            return None
        
        foot_vector_normalized = foot_vector / foot_norm
        
        # Calcular ángulo usando producto punto
        dot_product = np.clip(np.dot(vertical_down_vector, foot_vector_normalized), -1.0, 1.0)
        angle_rad = np.arccos(dot_product)
        angle_deg = np.degrees(angle_rad)
        
        return angle_deg
    
    def convert_to_clinical_angle(self, raw_angle: float) -> Tuple[float, str]:
        """
        Convierte ángulo absoluto a medición clínica de INVERSIÓN
        
        Sistema de medición (como goniómetro en imagen):
        - Vértice en TALÓN
        - Eje vertical = 0° (referencia neutra)
        - Brazo móvil: TALÓN → TOBILLO
        
        Ángulo RAW (desde vertical):
        - 0° = Pie completamente alineado verticalmente (NEUTRO perfecto)
        - 5-15° = INVERSIÓN leve
        - 15-30° = INVERSIÓN moderada  
        - >30° = INVERSIÓN alta
        
        Ángulo CLÍNICO (mismo que ángulo raw en este caso):
        - El ángulo ya está en formato clínico (0° = neutro)
        - No necesita conversión adicional
        
        Args:
            raw_angle: Ángulo absoluto medido desde vertical
        
        Returns:
            Tuple[clinical_angle, movement_type]
        """
        # En este sistema, el ángulo raw YA es el ángulo clínico
        # 0° = neutro, valores mayores = inversión
        
        if raw_angle <= THRESHOLD_NEUTRAL:
            # NEUTRO: ángulo muy pequeño (0-5°)
            clinical_angle = raw_angle
            movement_type = "NEUTRO"
        else:
            # INVERSIÓN: cualquier desviación de la vertical
            clinical_angle = raw_angle
            movement_type = "INVERSION"
        
        return clinical_angle, movement_type
    
    def get_angle_color(self, clinical_angle: float, movement_type: str) -> Tuple[int, int, int]:
        """
        Obtiene el color según el ángulo clínico
        
        Args:
            clinical_angle: Ángulo clínico (0° = neutro)
            movement_type: Tipo de movimiento
        
        Returns:
            Color BGR
        """
        cache_key = (int(clinical_angle), movement_type)
        if cache_key in self._color_cache:
            return self._color_cache[cache_key]
        
        if movement_type == "NEUTRO":
            color = COLORS['ANGLE_MINIMAL']
        elif movement_type == "INVERSION":
            if clinical_angle < 15:
                color = COLORS['ANGLE_LOW']
            elif clinical_angle < 25:
                color = COLORS['ANGLE_MID']
            elif clinical_angle < 35:
                color = COLORS['ANGLE_HIGH']
            else:
                color = COLORS['ANGLE_EXCESSIVE']
        else:  # EVERSION (no esperado pero posible)
            color = COLORS['TEXT_WARNING']
        
        self._color_cache[cache_key] = color
        return color
    
    def update_rom_tracking(self, clinical_angle: float, movement_type: str):
        """Actualiza el tracking de ROM para inversión"""
        if movement_type == "INVERSION":
            self.rom_inversion['current'] = clinical_angle
            self.rom_inversion['max'] = max(self.rom_inversion['max'], clinical_angle)
            self.rom_inversion['min'] = min(self.rom_inversion['min'], clinical_angle)
    
    def draw_landmarks_and_connections(self, image: np.ndarray, landmarks_px: Dict, 
                                      visibility: Dict) -> np.ndarray:
        """Dibuja los landmarks y conexiones del tobillo según goniómetro clínico"""
        foot = self.selected_foot
        
        # Verificar visibilidad (ahora incluye FOOT_INDEX)
        if not all([visibility[f'{foot}_KNEE'] > 0.5,
                   visibility[f'{foot}_ANKLE'] > 0.5,
                   visibility[f'{foot}_HEEL'] > 0.5,
                   visibility[f'{foot}_FOOT_INDEX'] > 0.5]):
            return image
        
        # Obtener posiciones
        knee = landmarks_px[f'{foot}_KNEE']
        ankle = landmarks_px[f'{foot}_ANKLE']
        heel = landmarks_px[f'{foot}_HEEL']
        foot_index = landmarks_px[f'{foot}_FOOT_INDEX']
        
        # ==== GONIÓMETRO CLÍNICO (VÉRTICE en TOBILLO) ====
        
        # 1. Línea vertical de referencia (0°) desde el TOBILLO hacia ABAJO
        vertical_length = 150
        vertical_end = (ankle[0], ankle[1] + vertical_length)  # Hacia abajo
        cv2.line(image, ankle, vertical_end, (0, 255, 0), 3, LINE_STYLE)  # Verde (brazo fijo)
        
        # 2. Brazo móvil: TOBILLO → DEDOS (donde se mide el ángulo)
        cv2.line(image, ankle, foot_index, (0, 165, 255), 4, LINE_STYLE)  # Naranja grueso (brazo móvil)
        
        # 3. Líneas auxiliares de contexto anatómico
        cv2.line(image, knee, ankle, (255, 255, 255), 2, LINE_STYLE)  # Blanco: Rodilla → Tobillo
        cv2.line(image, ankle, heel, (128, 128, 128), 2, LINE_STYLE)  # Gris: Tobillo → Talón
        
        # Dibujar landmarks
        cv2.circle(image, knee, 5, COLORS['LANDMARK_ACTIVE'], -1, LINE_STYLE)
        cv2.circle(image, ankle, 10, (255, 0, 255), -1, LINE_STYLE)  # TOBILLO (VÉRTICE - magenta, 10px)
        cv2.circle(image, heel, 6, (128, 128, 128), -1, LINE_STYLE)  # TALÓN (contexto - gris, 6px)
        cv2.circle(image, foot_index, 7, (255, 255, 0), -1, LINE_STYLE)  # DEDOS (punto final - cyan, 7px)
        
        # Etiquetas de landmarks
        cv2.putText(image, "TOBILLO (vertice)", (ankle[0] + 15, ankle[1] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1, LINE_STYLE)
        cv2.putText(image, "DEDOS", (foot_index[0] + 10, foot_index[1] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1, LINE_STYLE)
        
        return image
    
    def draw_angle_info(self, image: np.ndarray, ankle_pos: Tuple[int, int]):
        """Dibuja la información del ángulo cerca del TOBILLO (vértice del goniómetro)"""
        x, y = ankle_pos
        
        # Color según el ángulo
        color = self.get_angle_color(self.current_clinical_angle, self.movement_type)
        
        # Ángulo clínico (desde vertical = 0°)
        angle_text = f"{self.current_clinical_angle:.1f}deg"
        cv2.putText(image, angle_text, (x + 25, y - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2, LINE_STYLE)
        
        # Tipo de movimiento
        movement_text = self.movement_type
        cv2.putText(image, movement_text, (x + 25, y + 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, LINE_STYLE)
    
    def draw_rom_bar(self, image: np.ndarray):
        """Dibuja la barra de ROM para inversión"""
        h, w = image.shape[:2]
        bar_x = w - 60
        bar_y_start = 100
        bar_height = 300
        bar_width = 30
        
        # Fondo de la barra
        cv2.rectangle(image, (bar_x, bar_y_start), 
                     (bar_x + bar_width, bar_y_start + bar_height),
                     COLORS['BG_SEMI'], -1, LINE_STYLE)
        
        # Título
        cv2.putText(image, "ROM", (bar_x - 10, bar_y_start - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['TEXT_PRIMARY'], 1, LINE_STYLE)
        
        # Escala (0-35°)
        max_rom = ROM_INVERSION['MAX']
        
        # Marcadores de escala
        for angle in [0, 15, 25, 35]:
            y_pos = bar_y_start + bar_height - int((angle / max_rom) * bar_height)
            cv2.line(image, (bar_x - 5, y_pos), (bar_x, y_pos),
                    COLORS['TEXT_PRIMARY'], 1, LINE_STYLE)
            cv2.putText(image, f"{angle}", (bar_x - 30, y_pos + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, COLORS['TEXT_PRIMARY'], 1, LINE_STYLE)
        
        # Nivel actual de inversión
        if self.rom_inversion['current'] > 0:
            fill_height = int((self.rom_inversion['current'] / max_rom) * bar_height)
            fill_height = min(fill_height, bar_height)
            
            color = self.get_angle_color(self.rom_inversion['current'], "INVERSION")
            
            cv2.rectangle(image, (bar_x, bar_y_start + bar_height - fill_height),
                         (bar_x + bar_width, bar_y_start + bar_height),
                         color, -1, LINE_STYLE)
        
        # Máximo alcanzado
        if self.rom_inversion['max'] > 0:
            max_y = bar_y_start + bar_height - int((self.rom_inversion['max'] / max_rom) * bar_height)
            cv2.line(image, (bar_x, max_y), (bar_x + bar_width, max_y),
                    COLORS['TEXT_SUCCESS'], 2, LINE_STYLE)
    
    def draw_header_info(self, image: np.ndarray):
        """Dibuja información de encabezado"""
        h, w = image.shape[:2]
        
        # Fondo semitransparente
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (w, 100), COLORS['BG_DARK'], -1, LINE_STYLE)
        cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)
        
        # Título
        cv2.putText(image, "BIOTRACK - INVERSION TOBILLO (Vista FRONTAL)", (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['TEXT_PRIMARY'], 2, LINE_STYLE)
        
        # Info del pie analizado
        foot_text = f"Pie: {self.selected_foot}"
        cv2.putText(image, foot_text, (10, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['TEXT_SUCCESS'], 1, LINE_STYLE)
        
        # Sistema de medición (goniómetro)
        method_text = "Goniometro: Vertice en TOBILLO | 0deg = Neutro (vertical)"
        cv2.putText(image, method_text, (10, 72),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, LINE_STYLE)
        
        # Advertencia sobre precisión
        warning_text = "NOTA: Movimiento sutil - Mantener pie visible"
        cv2.putText(image, warning_text, (10, 92),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLORS['TEXT_WARNING'], 1, LINE_STYLE)
    
    def draw_stats_panel(self, image: np.ndarray):
        """Dibuja panel de estadísticas"""
        h, w = image.shape[:2]
        panel_x = 10
        panel_y = h - 120
        
        # Fondo
        overlay = image.copy()
        cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + 300, h - 10),
                     COLORS['BG_DARK'], -1, LINE_STYLE)
        cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)
        
        # Estadísticas
        stats_text = [
            f"Frames analizados: {self.stats['frames_analyzed']}",
            f"Con deteccion: {self.stats['frames_with_detection']}",
            f"Max inversion: {self.stats['max_inversion']:.1f}deg",
            f"Tiempo: {int(time.time() - self.stats['session_start'])}s"
        ]
        
        y_offset = panel_y + 20
        for text in stats_text:
            cv2.putText(image, text, (panel_x + 10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLORS['TEXT_PRIMARY'], 1, LINE_STYLE)
            y_offset += 20
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Procesa un frame y realiza el análisis del tobillo
        
        Args:
            frame: Frame de video (BGR)
        
        Returns:
            Tuple[frame_procesado, deteccion_exitosa]
        """
        self.stats['frames_analyzed'] += 1
        
        # Procesar con MediaPipe (escala reducida)
        frame_small = cv2.resize(frame, PROCESSING_SIZE)
        frame_rgb = cv2.cvtColor(frame_small, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)
        
        # Escalar de vuelta
        display_frame = frame.copy()
        h, w = display_frame.shape[:2]
        scale_x = w / PROCESSING_SIZE[0]
        scale_y = h / PROCESSING_SIZE[1]
        
        # Verificar detección
        if not results.pose_landmarks:
            self.draw_header_info(display_frame)
            cv2.putText(display_frame, "SIN DETECCION - Posicionate frente a la camara", 
                       (w//2 - 250, h//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['TEXT_ERROR'], 2, LINE_STYLE)
            return display_frame, False
        
        # Extraer landmarks
        landmarks = results.pose_landmarks.landmark
        foot = self.selected_foot
        
        landmarks_px = {}
        visibility = {}
        
        for key, lm_type in LANDMARKS[foot].items():
            lm = landmarks[lm_type]
            px_x = int(lm.x * w)
            px_y = int(lm.y * h)
            landmarks_px[f'{foot}_{key}'] = (px_x, px_y)
            visibility[f'{foot}_{key}'] = lm.visibility
        
        # Verificar visibilidad mínima (ahora incluye FOOT_INDEX)
        required_landmarks = [f'{foot}_KNEE', f'{foot}_ANKLE', f'{foot}_HEEL', f'{foot}_FOOT_INDEX']
        if not all(visibility[lm] > 0.5 for lm in required_landmarks):
            self.draw_header_info(display_frame)
            cv2.putText(display_frame, f"Pie {foot} NO visible - Ajusta posicion", 
                       (w//2 - 200, h//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['TEXT_WARNING'], 2, LINE_STYLE)
            return display_frame, False
        
        # Calcular ángulo con 4 landmarks (knee, ankle, heel, foot_index)
        knee_pos = np.array(landmarks_px[f'{foot}_KNEE'])
        ankle_pos = np.array(landmarks_px[f'{foot}_ANKLE'])
        heel_pos = np.array(landmarks_px[f'{foot}_HEEL'])
        foot_index_pos = np.array(landmarks_px[f'{foot}_FOOT_INDEX'])
        
        raw_angle = self.calculate_ankle_angle(knee_pos, ankle_pos, heel_pos, foot_index_pos)
        
        if raw_angle is None:
            self.draw_header_info(display_frame)
            return display_frame, False
        
        # Convertir a ángulo clínico
        clinical_angle, movement_type = self.convert_to_clinical_angle(raw_angle)
        
        # Suavizar ángulo
        self.angle_history.append(clinical_angle)
        smoothed_angle = np.mean(self.angle_history)
        
        # Actualizar estado
        self.current_angle = raw_angle
        self.current_clinical_angle = smoothed_angle
        self.movement_type = movement_type
        
        # Actualizar ROM
        self.update_rom_tracking(smoothed_angle, movement_type)
        
        # Actualizar estadísticas
        self.stats['frames_with_detection'] += 1
        if movement_type == "INVERSION":
            self.stats['max_inversion'] = max(self.stats['max_inversion'], smoothed_angle)
        
        # Visualización según modo
        mode = DISPLAY_MODES[CURRENT_DISPLAY_MODE]
        
        # Dibujar landmarks y conexiones
        if mode['show_skeleton']:
            self.draw_landmarks_and_connections(display_frame, landmarks_px, visibility)
        
        # Dibujar información del ángulo (cerca del TOBILLO - vértice del goniómetro)
        if mode['show_measurements']:
            self.draw_angle_info(display_frame, landmarks_px[f'{foot}_ANKLE'])
        
        # Dibujar barra de ROM
        if mode['show_rom_bar']:
            self.draw_rom_bar(display_frame)
        
        # Dibujar encabezado
        self.draw_header_info(display_frame)
        
        # Dibujar estadísticas
        if mode['show_stats']:
            self.draw_stats_panel(display_frame)
        
        return display_frame, True
    
    def release(self):
        """Libera recursos"""
        self.pose.close()


# ======================== FUNCIONES DE UTILIDAD ========================
def select_foot() -> str:
    """
    Solicita al usuario que seleccione el pie a analizar
    
    Returns:
        'LEFT' o 'RIGHT'
    """
    print("\n" + "="*70)
    print("BIOTRACK - ANÁLISIS DE TOBILLO (Vista FRONTAL)")
    print("="*70)
    print("\nMovimiento: INVERSIÓN del pie")
    print("\nInstrucciones de posicionamiento:")
    print("  - Colócate DE FRENTE a la cámara")
    print("  - Asegúrate de que TODO el pie esté visible")
    print("  - La rodilla, tobillo y talón deben verse claramente")
    print("\nADVERTENCIA:")
    print("  La inversión es un movimiento MUY SUTIL")
    print("  Las mediciones pueden tener imprecisiones debido a")
    print("  limitaciones de landmarks del pie en MediaPipe")
    print("="*70)
    
    while True:
        print("\n¿Qué pie deseas analizar?")
        print("  1. Pie IZQUIERDO")
        print("  2. Pie DERECHO")
        
        choice = input("\nSelecciona una opción (1 o 2): ").strip()
        
        if choice == '1':
            return 'LEFT'
        elif choice == '2':
            return 'RIGHT'
        else:
            print("❌ Opción inválida. Por favor ingresa 1 o 2.")


def print_rom_summary(analyzer: AnkleFrontalAnalyzer):
    """Imprime resumen de ROM al finalizar"""
    print("\n" + "="*70)
    print("RESUMEN DE RANGO DE MOVIMIENTO (ROM)")
    print("="*70)
    
    print(f"\nPie analizado: {analyzer.selected_foot}")
    
    print("\nINVERSIÓN:")
    if analyzer.rom_inversion['max'] > 0:
        print(f"  Máximo alcanzado: {analyzer.rom_inversion['max']:.1f}°")
        print(f"  Rango normal: 0-{ROM_INVERSION['MAX']}°")
        
        if analyzer.rom_inversion['max'] >= ROM_INVERSION['TARGET']:
            print(f"  ✓ ROM alcanzado ({ROM_INVERSION['TARGET']}° objetivo)")
        else:
            deficit = ROM_INVERSION['TARGET'] - analyzer.rom_inversion['max']
            print(f"  ⚠ Déficit de {deficit:.1f}° respecto al objetivo ({ROM_INVERSION['TARGET']}°)")
    else:
        print("  No se detectó movimiento de inversión")
    
    print("\nESTADÍSTICAS DE SESIÓN:")
    print(f"  Frames totales: {analyzer.stats['frames_analyzed']}")
    print(f"  Frames con detección: {analyzer.stats['frames_with_detection']}")
    if analyzer.stats['frames_analyzed'] > 0:
        detection_rate = (analyzer.stats['frames_with_detection'] / analyzer.stats['frames_analyzed']) * 100
        print(f"  Tasa de detección: {detection_rate:.1f}%")
    
    duration = time.time() - analyzer.stats['session_start']
    print(f"  Duración: {int(duration)}s")
    
    print("="*70)


# ======================== FUNCIÓN PRINCIPAL ========================
def main():
    """Función principal"""
    
    # 1. Selección del pie
    selected_foot = select_foot()
    
    print(f"\n✓ Pie seleccionado: {selected_foot}")
    print("\nIniciando análisis...")
    print("Presiona 'q' para salir")
    print("Presiona 'm' para cambiar modo de visualización")
    print("Presiona 'r' para resetear ROM\n")
    
    # 2. Inicializar analizador
    analyzer = AnkleFrontalAnalyzer(selected_foot)
    
    # 3. Inicializar cámara
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: No se pudo abrir la cámara")
        return
    
    # Configurar resolución
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # 4. Loop principal
    global CURRENT_DISPLAY_MODE
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Error al leer frame de la cámara")
                break
            
            # Procesar frame
            processed_frame, detection_ok = analyzer.process_frame(frame)
            
            # Mostrar
            cv2.imshow('BIOTRACK - Tobillo Frontal (Inversion)', processed_frame)
            
            # Controles de teclado
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("\n🛑 Saliendo...")
                break
            elif key == ord('m'):
                modes = list(DISPLAY_MODES.keys())
                current_idx = modes.index(CURRENT_DISPLAY_MODE)
                CURRENT_DISPLAY_MODE = modes[(current_idx + 1) % len(modes)]
                print(f"Modo de visualización: {CURRENT_DISPLAY_MODE}")
            elif key == ord('r'):
                analyzer.rom_inversion = {'min': float('inf'), 'max': 0.0, 'current': 0.0}
                print("ROM reseteado")
    
    except KeyboardInterrupt:
        print("\n🛑 Interrumpido por usuario")
    
    finally:
        # 5. Mostrar resumen
        print_rom_summary(analyzer)
        
        # 6. Liberar recursos
        cap.release()
        cv2.destroyAllWindows()
        analyzer.release()
        print("\n✓ Recursos liberados correctamente")


if __name__ == "__main__":
    main()
