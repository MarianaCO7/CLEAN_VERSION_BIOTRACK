"""
🦶 ANALIZADOR DE TOBILLO COMPLETO
🎯 Dorsiflexión, plantiflexión y análisis postural del pie
📐 Medición: Rodilla-Tobillo-Pie (tobillo como vértice)
"""

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import numpy as np
import cv2
import math
import json
from core.base_analyzer import BaseJointAnalyzer
from core.orientation_detector import AdaptiveOrientationDetector

class AnkleAnalyzer(BaseJointAnalyzer):
    """🦶 Analizador especializado en tobillos"""
    
    def __init__(self):
        super().__init__("Ankle")
        
        # 🆕 INICIALIZAR MEDIAPIPE EXPLÍCITAMENTE (patrón exitoso)
        try:
            import mediapipe as mp
            self.mp_pose = mp.solutions.pose
            self.pose = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                enable_segmentation=False,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5
            )
            self.mp_draw = mp.solutions.drawing_utils
            print("✅ MediaPipe inicializado correctamente para tobillo")
            
        except Exception as e:
            print(f"❌ Error inicializando MediaPipe tobillo: {e}")
            raise
        
        self.orientation_detector = AdaptiveOrientationDetector()
        
        # 🦶 RANGOS NORMATIVOS DE TOBILLO
        self.normal_ranges = {
            "ankle_dorsiflexion": {"min": 90, "max": 120, "functional": 105},
            "ankle_plantiflexion": {"min": 45, "max": 90, "functional": 70},
            "ankle_neutral": {"min": 85, "max": 95, "optimal": 90},
            "ankle_separation": {"min": 10, "max": 30, "functional": 20}
        }
        
        # 🎯 SOPORTE MULTI-EJERCICIO
        self.current_exercise = "flexion"  # Default exercise
        
        # 🧭 FORZAR ORIENTACIÓN (opcional, para override del JSON)
        self.forced_orientation = None  # None = auto-detect, 'SAGITAL'/'FRONTAL' = forzar
    
    def set_forced_orientation(self, orientation: str):
        """
        🧭 Forzar orientación desde JSON (override del detector automático)
        
        Args:
            orientation: 'SAGITAL', 'FRONTAL', 'POSTERIOR', etc.
        """
        self.forced_orientation = orientation
        print(f"🧭 ANKLE: Orientación forzada a {orientation} (desde JSON)")
    
    def set_current_exercise(self, exercise_type: str):
        """
        Configura el ejercicio actual para el análisis
        🆕 Ahora lee camera_orientation desde exercises.json
        
        Args:
            exercise_type: Tipo de ejercicio ('flexion', 'dorsiflexion', 'inversion')
        """
        valid_exercises = ['flexion', 'dorsiflexion', 'inversion']
        if exercise_type in valid_exercises:
            self.current_exercise = exercise_type
            print(f"🎯 Ejercicio de tobillo configurado: {exercise_type}")
            
            # 🆕 CARGAR camera_orientation desde JSON (como hip/elbow/knee)
            if not hasattr(self, 'exercise_configs'):
                # Cargar exercises.json una sola vez
                config_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'biomechanical_web_interface', 'config', 'exercises.json'
                )
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.exercise_configs = data['segments']['ankle']['exercises']
                except Exception as e:
                    print(f"⚠️ Error cargando exercises.json: {e}")
                    self.exercise_configs = {}
            
            # 🆕 OBTENER camera_orientation del ejercicio actual
            if exercise_type in self.exercise_configs:
                exercise_data = self.exercise_configs[exercise_type]
                self.current_camera_orientation = exercise_data.get('camera_orientation', 'SAGITAL')
                print(f"📷 Camera orientation para {exercise_type}: {self.current_camera_orientation}")
            else:
                # Default: tobillo dorsiflexion/plantiflexion siempre es SAGITAL (perfil)
                self.current_camera_orientation = 'SAGITAL'
                print(f"⚠️ No se encontró config para {exercise_type}, usando 'SAGITAL' por defecto")
        else:
            print(f"⚠️ Ejercicio inválido: {exercise_type}. Usando flexion por defecto.")
            self.current_exercise = "flexion"
            self.current_camera_orientation = 'SAGITAL'
        
        # 🎯 TIPOS DE EJERCICIOS ESPECÍFICOS
        self.exercise_types = {
            "dorsiflexion": "Dorsiflexión (punta arriba)",
            "plantiflexion": "Plantiflexión (punta abajo)", 
            "calf_raise": "Elevación de gemelos",
            "heel_walk": "Caminar en talones",
            "ankle_circles": "Círculos de tobillo",
            "balance": "Equilibrio en un pie"
        }

    def get_required_landmarks(self):
        """📍 Puntos necesarios para análisis de tobillo"""
        return [
            25, 26,  # Rodillas
            27, 28,  # Tobillos  
            31, 32   # Pies (índice del pie)
        ]

    def check_required_points_visible(self, landmarks):
        """✅ Verificar visibilidad - PERMISIVO como test_ankle_movements.py
        
        🎯 FILOSOFÍA: Si MediaPipe detectó pose, intentar calcular
        ❌ ANTES: Threshold 0.3 muy estricto → rechazaba poses válidas
        ✅ AHORA: Solo verificar que existan landmarks básicos
        """
        
        if not landmarks or len(landmarks) < 33:
            # print("❌ ANKLE CHECK: landmarks insuficientes")  # 🔇 COMENTADO - Muy repetitivo
            return False
        
        # 🆕 DETECCIÓN DE EJERCICIOS FRONTALES
        is_frontal_exercise = self.current_exercise in ['inversion', 'eversion', 'inversion_eversion']
        
        # 🦶 PUNTOS MÍNIMOS: Solo tobillos (27, 28) - MUY PERMISIVO
        # Si MediaPipe detectó pose, probablemente los tobillos sean visibles
        ankle_points = [27, 28]
        
        # 🆕 Threshold más bajo para ejercicios frontales
        threshold = 0.03 if is_frontal_exercise else 0.05
        
        # Verificar que al menos UN tobillo tenga visibilidad > threshold (ultra-bajo)
        ankle_visibilities = [landmarks[idx].visibility if idx < len(landmarks) else 0 
                             for idx in ankle_points]
        
        any_ankle_visible = any(v > threshold for v in ankle_visibilities)
        
        # 🔇 COMENTADO - Prints cada frame causan lag
        # if any_ankle_visible:
        #     print(f"✅ ANKLE CHECK: Al menos un tobillo visible {ankle_visibilities}")
        #     return True
        # else:
        #     print(f"❌ ANKLE CHECK: Ningún tobillo visible {ankle_visibilities}")
        #     return False
        
        return any_ankle_visible
    
    def detect_side_and_visibility(self, landmarks):
        """
        🎯 NUEVO MÉTODO - ADAPTADO DE test_ankle_movements.py (línea 162)
        
        Detecta qué lado del cuerpo está visible y orientación (PERFIL vs FRONTAL)
        Retorna: view_type, side, confidence, orientation, facing_direction (5 valores)
        
        📐 Lógica:
        - avg_distance > 0.12 y ambos lados visibles → FRONTAL
        - avg_distance < 0.12 o un lado dominante → PERFIL (con side detection)
        """
        
        if not landmarks or len(landmarks) < 33:
            return "UNKNOWN", None, 0.0, "UNKNOWN", "UNKNOWN"
        
        try:
            # Obtener puntos clave
            left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            left_knee = landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE.value]
            right_knee = landmarks[self.mp_pose.PoseLandmark.RIGHT_KNEE.value]
            left_ankle = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value]
            right_ankle = landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE.value]
            nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
            
            # Calcular visibilidad de cada pierna
            left_visibility = (left_knee.visibility + left_ankle.visibility) / 2
            right_visibility = (right_knee.visibility + right_ankle.visibility) / 2
            
            # Calcular distancia entre rodillas (en coordenadas normalizadas)
            knee_distance = abs(right_knee.x - left_knee.x)
            
            # Calcular distancia entre tobillos
            ankle_distance = abs(right_ankle.x - left_ankle.x)
            
            # Promedio de visibilidad y distancias
            avg_visibility = (left_visibility + right_visibility) / 2
            avg_distance = (knee_distance + ankle_distance) / 2
            
            # Calcular facing_direction basado en la posición de la nariz
            nose_x = nose.x
            shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2
            nose_offset = nose_x - shoulder_center_x
            
            # Determinar facing_direction con threshold más estricto
            if abs(nose_offset) < 0.05:  # Threshold para frontal
                facing_direction = "FRONTAL"
            elif nose_offset < 0:
                facing_direction = "IZQUIERDA"
            else:
                facing_direction = "DERECHA"
            
            # 🎯 DETERMINAR VISTA: FRONTAL vs PERFIL
            if avg_distance > 0.12 and avg_visibility > 0.5 and left_visibility > 0.4 and right_visibility > 0.4:
                # FRONTAL: Ambas piernas visibles con buena separación
                view_type = "FRONTAL"
                side = None  # No aplica en frontal
                confidence = min(avg_visibility, 1.0)
                orientation = "FRONTAL"
                
            else:
                # PERFIL: Una pierna dominante
                view_type = "SAGITAL"  # ✅ CORREGIDO: Usar "SAGITAL" (consistente con otros analyzers)
                
                # 🪞 ESPEJO MediaPipe: left_ankle (landmark 27) = tobillo DERECHO usuario
                #                      right_ankle (landmark 28) = tobillo IZQUIERDO usuario
                # Determinar qué lado está más visible
                if left_visibility > right_visibility:
                    # Landmark LEFT más visible → tobillo DERECHO del usuario
                    side = 'right'  # ✅ Corregido: devolver 'right' (lado usuario, no landmark)
                    confidence = left_visibility
                else:
                    # Landmark RIGHT más visible → tobillo IZQUIERDO del usuario
                    side = 'left'  # ✅ Corregido: devolver 'left' (lado usuario, no landmark)
                    confidence = right_visibility
                
                orientation = "SAGITAL"
            
            return view_type, side, confidence, orientation, facing_direction
            
        except Exception as e:
            print(f"⚠️ Error en detect_side_and_visibility: {e}")
            return "UNKNOWN", None, 0.0, "UNKNOWN", "UNKNOWN"

    def validate_orientation_by_facing(self, landmarks, force_accept_after_seconds=15):
        """
        🎯 VALIDACIÓN MODERNA: Usa facing_direction (mirada) NO geometría de hombros
        
        Compara la orientación REQUERIDA (camera_orientation del ejercicio)
        con la DETECTADA (facing_direction basado en posición de nariz)
        
        Args:
            landmarks: MediaPipe landmarks
            force_accept_after_seconds: Segundos después de los cuales aceptar automáticamente (default: 15)
        
        Returns:
            bool: True si orientación correcta, False si incorrecta
            
        Lógica:
            - Ejercicio FRONTAL → requiere facing='FRONTAL'
            - Ejercicio SAGITAL (dorsiflexion/plantiflexion) → requiere facing='IZQUIERDA' o 'DERECHA'
            - DESPUÉS DE N SEGUNDOS → Aceptar automáticamente (evitar bloqueo permanente)
        """
        try:
            # ⏱️ TIMEOUT AUTOMÁTICO: Si pasan X segundos sin validar, aceptar
            if not hasattr(self, '_validation_start_time'):
                import time
                self._validation_start_time = time.time()
            
            elapsed_time = time.time() - self._validation_start_time
            
            if elapsed_time > force_accept_after_seconds:
                if not hasattr(self, '_force_accepted'):
                    print(f"⏱️ [ANKLE] Timeout {force_accept_after_seconds}s alcanzado - ACEPTANDO orientación automáticamente")
                    self._force_accepted = True
                return True  # ✅ Aceptar después de timeout
            
            # 🔍 DETECTAR orientación actual (5 valores)
            view_type, side, confidence, orientation, facing_direction = self.detect_side_and_visibility(landmarks)
            
            # 🎯 NORMALIZAR valores para comparación
            required_orientation = self.current_camera_orientation.upper()  # 'FRONTAL' o 'SAGITAL'
            detected_facing = facing_direction.upper()  # 'FRONTAL', 'IZQUIERDA', 'DERECHA'
            
            # 🔇 CACHE: Solo imprimir si cambia el estado (evitar spam que causa lag)
            cache_key = f"{detected_facing}_{required_orientation}"
            if not hasattr(self, '_last_validation_log') or self._last_validation_log != cache_key:
                print(f"🧭 [ANKLE validate_orientation_by_facing]")
                print(f"   Requerida: {required_orientation}, Detectada: {detected_facing} (view={view_type})")
                print(f"   ⏱️ Tiempo: {elapsed_time:.1f}s / {force_accept_after_seconds}s (auto-accept)")
                self._last_validation_log = cache_key
            
            # 🎯 VALIDACIÓN SEGÚN TIPO DE EJERCICIO
            if required_orientation == 'FRONTAL':
                # ✅ Ejercicio FRONTAL: necesita mirar de frente
                is_valid = (detected_facing == 'FRONTAL')
                if is_valid:
                    self._validation_start_time = time.time()  # Reset timer si válido
                return is_valid
                
            elif required_orientation == 'SAGITAL':
                # ✅ Ejercicio SAGITAL: necesita mirar IZQUIERDA o DERECHA (perfil)
                is_valid = (detected_facing in ['IZQUIERDA', 'DERECHA'])
                if is_valid:
                    self._validation_start_time = time.time()  # Reset timer si válido
                return is_valid
                
            else:
                # ⚠️ Orientación desconocida - aceptar por defecto
                print(f"⚠️ Orientación requerida desconocida: {required_orientation}")
                return True
                
        except Exception as e:
            print(f"❌ Error validando orientación ANKLE: {e}")
            return True

    def detect_pose(self, frame):
        """🦶 DETECTAR POSE - Método explícito para tobillo"""
        
        try:
            # Convertir BGR a RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Procesar con MediaPipe
            results = self.pose.process(rgb_frame)
            
            if results.pose_landmarks:
                return results.pose_landmarks.landmark
            else:
                return None
                
        except Exception as e:
            print(f"⚠️ Error en detect_pose tobillo: {e}")
            return None

    def calculate_joint_angles(self, landmarks, frame_dimensions):
        """📐 Calcular ángulos de ambos tobillos - ACTUALIZADO CON DETECT_SIDE_AND_VISIBILITY"""
        
        h, w = frame_dimensions
        
        # 🆕 PASO 1: USAR NUEVO MÉTODO detect_side_and_visibility() - 5 VALORES
        view_type, detected_side, confidence, orientation_detected, facing_direction = self.detect_side_and_visibility(landmarks)
        
        # 🧭 PRIORIDAD: JSON > detect_side_and_visibility > fallback
        if self.forced_orientation:
            # JSON tiene prioridad máxima
            current_orientation = self.forced_orientation
            orientation_info = {
                'orientation': current_orientation,
                'confidence': 1.0,
                'method': 'forced_from_json',
                'view_type': view_type,  # Guardar info del detector
                'detected_side': detected_side
            }
        else:
            # Usar detección automática
            current_orientation = orientation_detected
            orientation_info = {
                'orientation': current_orientation,
                'confidence': confidence,
                'method': 'detect_side_and_visibility',
                'view_type': view_type,
                'detected_side': detected_side
            }
        
        # 🦶 ANALIZAR AMBOS TOBILLOS (CON PROTECCIÓN)
        try:
            right_ankle_result = self._analyze_single_ankle(landmarks, "RIGHT", w, h, current_orientation)
            left_ankle_result = self._analyze_single_ankle(landmarks, "LEFT", w, h, current_orientation)
            
        except Exception as e:
            print(f"⚠️ Error en análisis de tobillos: {e}")
            # Crear resultados por defecto
            right_ankle_result = {
                'status': 'ERROR', 'angle': 90.0, 'raw_angle': 90.0, 'quality': 0,
                'movement_type': 'NEUTRAL',
                'points': {'knee': None, 'ankle': None, 'foot': None}
            }
            left_ankle_result = {
                'status': 'ERROR', 'angle': 90.0, 'raw_angle': 90.0, 'quality': 0,
                'movement_type': 'NEUTRAL',
                'points': {'knee': None, 'ankle': None, 'foot': None}
            }
        
        # 🔧 APLICAR FILTROS TEMPORALES
        try:
            # ✅ TEMPORAL FILTER ACTIVADO - Suaviza ángulos para mediciones más estables
            filtered_angle_r = self.apply_temporal_filter(right_ankle_result['angle'], 'right_ankle')
            filtered_angle_l = self.apply_temporal_filter(left_ankle_result['angle'], 'left_ankle')
            
        except Exception as e:
            print(f"⚠️ Error en filtro temporal: {e}")
            filtered_angle_r = float(right_ankle_result['angle'])
            filtered_angle_l = float(left_ankle_result['angle'])
        
        # 📊 ESTRUCTURA DE RESULTADO (CON PROTECCIÓN TOTAL)
        try:
            # 🎯 DETERMINAR primary_leg PRIMERO
            primary_leg = self._select_primary_leg(landmarks, right_ankle_result, left_ankle_result)
            
            # 🔧 FILTRADO CRÍTICO: En SAGITAL/PERFIL, anular el lado NO-primary
            # Esto evita que el handler use ángulos basura del pie lejano
            if current_orientation == 'SAGITAL' or view_type == 'PERFIL':
                if primary_leg == 'RIGHT':
                    # Solo RIGHT válido, LEFT = None
                    filtered_angle_l = None
                    left_ankle_result['quality'] = 0
                elif primary_leg == 'LEFT':
                    # Solo LEFT válido, RIGHT = None  
                    filtered_angle_r = None
                    right_ankle_result['quality'] = 0
            
            # 🆕 CLASIFICACIÓN ROM (6 niveles - test línea 281)
            right_classification = self._classify_ankle_movement(filtered_angle_r) if filtered_angle_r is not None else 'UNKNOWN'
            left_classification = self._classify_ankle_movement(filtered_angle_l) if filtered_angle_l is not None else 'UNKNOWN'
            
            # 🪞 INTERCAMBIO ESPEJO MediaPipe (siguiendo patrón knee exitoso - líneas 194-197)
            # MediaPipe: left_ankle (27) = tobillo DERECHO usuario
            #            right_ankle (28) = tobillo IZQUIERDO usuario
            # Intercambiamos antes de return para que coincida con lado real
            raw_right_corrected = left_ankle_result['raw_angle']   # ✅ Landmark LEFT = tobillo DERECHO
            raw_left_corrected = right_ankle_result['raw_angle']   # ✅ Landmark RIGHT = tobillo IZQUIERDO
            filtered_right_corrected = filtered_angle_l            # ✅ Filtrado display
            filtered_left_corrected = filtered_angle_r             # ✅ Filtrado display
            right_classification_corrected = left_classification   # ✅ Clasificación ROM
            left_classification_corrected = right_classification   # ✅ Clasificación ROM
            right_quality_corrected = left_ankle_result['quality'] # ✅ Quality
            left_quality_corrected = right_ankle_result['quality'] # ✅ Quality
            
            angles = {
                'right_ankle': filtered_right_corrected,           # ✅ Intercambiado
                'left_ankle': filtered_left_corrected,             # ✅ Intercambiado
                'raw_right': raw_right_corrected,                  # ✅ Intercambiado para ROM tracking
                'raw_left': raw_left_corrected,                    # ✅ Intercambiado para ROM tracking
                'right_movement_type': right_classification_corrected,  # ✅ Intercambiado
                'left_movement_type': left_classification_corrected,    # ✅ Intercambiado
                'view_type': view_type,  # 🆕 PERFIL/FRONTAL del detector
                'positions': {
                    'knee_r': left_ankle_result['points']['knee'],    # ✅ Intercambiado
                    'ankle_r': left_ankle_result['points']['ankle'],  # ✅ Intercambiado
                    'foot_r': left_ankle_result['points']['foot'],    # ✅ Intercambiado
                    'knee_l': right_ankle_result['points']['knee'],   # ✅ Intercambiado
                    'ankle_l': right_ankle_result['points']['ankle'], # ✅ Intercambiado
                    'foot_l': right_ankle_result['points']['foot']    # ✅ Intercambiado
                },
                'orientation_info': orientation_info,
                'primary_leg': primary_leg,
                'right_ankle_quality': right_quality_corrected,    # ✅ Intercambiado
                'left_ankle_quality': left_quality_corrected       # ✅ Intercambiado
            }
            
            return angles
            
        except Exception as e:
            print(f"⚠️ Error creando estructura final: {e}")
            # Estructura mínima por defecto
            return {
                'right_ankle': 90.0, 'left_ankle': 90.0, 'raw_right': 90.0, 'raw_left': 90.0,
                'right_movement_type': 'NEUTRAL', 'left_movement_type': 'NEUTRAL',
                'view_type': 'UNKNOWN',
                'positions': {k: None for k in ['knee_r', 'ankle_r', 'foot_r', 'knee_l', 'ankle_l', 'foot_l']},
                'orientation_info': {'orientation': 'FRONTAL', 'confidence': 0.5},
                'primary_leg': 'BOTH', 'right_ankle_quality': 0, 'left_ankle_quality': 0
            }
    
    def _classify_ankle_movement(self, angle):
        """
        🆕 CLASIFICACIÓN ROM 6 NIVELES - ADAPTADO DE test_ankle_movements.py (línea 281)
        
        Sistema de clasificación (test ankle):
        - angle > 100° → DORSIFLEXION (punta arriba)
        - angle < 80° → PLANTIFLEXION (punta abajo)
        - 80-100° → NEUTRAL (posición intermedia)
        
        📐 Rangos anatómicos (Norkin & White 2016):
        - Neutral: ~90° (pie perpendicular a pierna)
        - Dorsiflexión: 90° a 110° (ROM +20°)
        - Plantiflexión: 90° a 40° (ROM -50°)
        
        🚨 VALIDACIÓN LÍMITES ANATÓMICOS:
        - Mínimo: 40° (plantiflexión máxima)
        - Máximo: 110° (dorsiflexión máxima)
        - Fuera de rango: ERROR de detección
        """
        
        if angle is None:
            return 'UNKNOWN'
        
        try:
            angle_val = float(angle)
            
            # 🚨 VALIDACIÓN ANATÓMICA: Rechazar ángulos imposibles
            if angle_val < 40 or angle_val > 110:
                print(f"⚠️ Ángulo NO anatómico detectado: {angle_val:.1f}° (rango válido: 40-110°)")
                return "ERROR"  # Ángulo fuera de límites anatómicos
            
            # 🎯 CLASIFICACIÓN EXACTA DEL TEST (dentro de rango anatómico)
            if angle_val > 100:
                return "DORSIFLEXION"  # Punta arriba
            elif angle_val < 80:
                return "PLANTIFLEXION"  # Punta abajo
            else:
                return "NEUTRAL"  # Rango 80-100°
                
        except (ValueError, TypeError):
            return 'UNKNOWN'

    def _analyze_single_ankle(self, landmarks, ankle_side, w, h, orientation):
        """
        🦶 ANALIZAR UN TOBILLO - MÉTODO CIENTÍFICO MEJORADO
        📐 Calcula ángulo INTERNO: rodilla-tobillo-pie
        🎯 Replica EXACTAMENTE el goniómetro manual clínico
        🔬 Migrado desde knee_analyzer con todas las mejoras
        """
        
        # Seleccionar landmarks según lado
        if ankle_side == 'RIGHT':
            knee_idx, ankle_idx, foot_idx = 26, 28, 32  # Derecha
        else:
            knee_idx, ankle_idx, foot_idx = 25, 27, 31  # Izquierda
        
        # 🧭 THRESHOLDS ADAPTATIVOS POR ORIENTACIÓN
        # SAGITAL (perfil): Thresholds MUY BAJOS (igual que test - calcular aunque visibility baja)
        # FRONTAL: Thresholds normales
        if orientation == 'SAGITAL':
            threshold_knee = 0.05    # ✅ Ultra-bajo para perfil (test no valida)
            threshold_ankle = 0.05   # ✅ Ultra-bajo para perfil
            threshold_foot = 0.05    # ✅ Ultra-bajo para perfil
        else:
            # FRONTAL: Thresholds más estrictos (ambos pies visibles)
            threshold_knee = 0.15
            threshold_ankle = 0.15
            threshold_foot = 0.10
        
        # ✅ CAMBIO: Calcular SIEMPRE si landmarks existen (como test)
        # Solo verificar que landmarks existan, NO rechazar por visibilidad baja
        try:
            # Intentar obtener puntos (pueden tener visibility baja pero estar presentes)
            knee = [landmarks[knee_idx].x * w, landmarks[knee_idx].y * h]
            ankle = [landmarks[ankle_idx].x * w, landmarks[ankle_idx].y * h]
            foot = [landmarks[foot_idx].x * w, landmarks[foot_idx].y * h]
        except (IndexError, AttributeError) as e:
            # Solo fallar si landmarks NO EXISTEN (índice fuera de rango)
            print(f"⚠️ Landmarks no existen para {ankle_side}: {e}")
            return {'angle': 0, 'movement_type': 'ERROR', 'quality': 0, 'points': {'knee': None, 'ankle': None, 'foot': None}}
        
        # 🎯 CÁLCULO CIENTÍFICO: Ángulo interno de 3 puntos (como goniómetro)
        raw_angle = self.calculate_angle_biomechanical(knee, ankle, foot)
        
        # � SISTEMA DE MEDICIÓN TOBILLO (Norkin & White 2016):
        # ========================================================
        # 🔹 NEUTRAL (pie perpendicular a pierna): ~90°
        # 🔹 DORSIFLEXIÓN (punta arriba): 90° → 110° (ROM +20° máximo)
        # 🔹 PLANTIFLEXIÓN (punta abajo): 90° → 40° (ROM -50° máximo)
        # 
        # ⚠️ DIFERENCIA CON GONIOMETRÍA CLÍNICA:
        #    - Clínica: Neutral=0°, Dorsiflex=0-20°, Plantiflex=0-50°
        #    - Este código: Ángulo interno 3-puntos (Neutral=90°)
        #    - Conversión: ROM_clínico = |ángulo_medido - 90°|
        
        # �🔄 INVERSIÓN DE ÁNGULO - REQUIERE VALIDACIÓN
        # ⚠️ IMPORTANTE: Probar en posición neutral (persona de pie):
        #    - Si raw_angle ~90°: NO invertir (usar directo)
        #    - Si raw_angle ~180°: SÍ invertir (usar 180 - raw_angle)
        # 📊 Comportamiento esperado:
        #    - Neutral (pie plano): ~90°
        #    - Dorsiflexión (punta arriba): >90° (aumenta)
        #    - Plantiflexión (punta abajo): <90° (disminuye)
        
        # 🧪 MODO TESTING: Usar directo para verificar
        # angle = raw_angle  # ❌ Testing mostró ~110-116° en neutral (esperado 90°)
        
        # 🔧 CALIBRACIÓN CRÍTICA BASADA EN TESTING REAL:
        # Testing 2 reveló ASIMETRÍA GEOMÉTRICA:
        # - RIGHT: neutral=87°, plantiflex=76° (BAJA correctamente) ✅
        # - LEFT: neutral=90°, plantiflex=98° (SUBE incorrectamente) ❌
        # 
        # CAUSA: Vectores rodilla→tobillo apuntan en direcciones opuestas
        # SOLUCIÓN: Inversión condicional por lado
        
        if ankle_side == 'RIGHT':
            # Lado derecho: Calibración simple
            angle = raw_angle - 23
        else:  # LEFT
            # Lado izquierdo: Inversión + calibración
            # raw ~110° → 180-110=70° +23=93° (neutral correcto)
            # raw ~90° → 180-90=90° +23=113° → necesita ajuste
            # FÓRMULA CORRECTA: Invertir primero, luego calibrar
            angle = 180 - raw_angle + 23
        
        # 🔍 APLICAR FILTRO TEMPORAL (mejora de estabilidad)
        filter_key = f'{ankle_side.lower()}_ankle'
        filtered_angle = self.apply_temporal_filter(angle, filter_key)
        
        # Calidad de detección (3 factores) - UMBRALES ADAPTATIVOS
        quality_score = 0
        if landmarks[knee_idx].visibility > threshold_knee: quality_score += 1
        if landmarks[ankle_idx].visibility > threshold_ankle: quality_score += 1
        if landmarks[foot_idx].visibility > threshold_foot: quality_score += 1
        
        # Determinar tipo de movimiento (dorsiflexión/plantiflexión)
        # Neutral: ~90°, Dorsiflexión: >90° (punta arriba), Plantiflexión: <90° (punta abajo)
        if filtered_angle > 100:
            movement_type = 'DORSIFLEXION'  # Punta hacia arriba (90°-120°)
        elif filtered_angle < 80:
            movement_type = 'PLANTIFLEXION'  # Punta hacia abajo (45°-90°)
        else:
            movement_type = 'NEUTRAL'  # Posición neutra (80°-100°)
        
        return {
            'angle': filtered_angle,
            'raw_angle': angle,
            'movement_type': movement_type,
            'quality': quality_score / 3.0,  # Normalizar a 0-1
            'points': {'knee': knee, 'ankle': ankle, 'foot': foot}
        }

    def _select_primary_leg(self, landmarks, right_result, left_result):
        """
        🎯 SELECCIONAR PIERNA PRINCIPAL en vista SAGITAL
        📐 Prioridad: 1) Z-depth (más cerca), 2) Calidad, 3) Ángulo válido, 4) Visibilidad
        🔬 Migrado desde knee_analyzer con todas las mejoras
        
        🪞 CRÍTICO: Tomar en cuenta espejo MediaPipe al comparar Z-depth
        - landmarks[27] (LEFT) = tobillo DERECHO real usuario
        - landmarks[28] (RIGHT) = tobillo IZQUIERDO real usuario
        """
        right_quality = right_result.get('quality', 0)
        left_quality = left_result.get('quality', 0)
        right_angle = right_result.get('angle', 0)
        left_angle = left_result.get('angle', 0)
        
        # 🎯 PRIORIDAD 1: Z-DEPTH (pierna más cercana a la cámara)
        # MediaPipe usa coordenada Z donde menor valor = más cerca
        # 🪞 INVERTIDO: landmarks[27] = tobillo DERECHO real, landmarks[28] = tobillo IZQUIERDO real
        right_ankle_z = landmarks[27].z if hasattr(landmarks[27], 'z') else 0  # ✅ Landmark LEFT = tobillo DERECHO
        left_ankle_z = landmarks[28].z if hasattr(landmarks[28], 'z') else 0   # ✅ Landmark RIGHT = tobillo IZQUIERDO
        
        # 🐛 DEBUG: Ver Z-depths para diagnosticar
        print(f"🔍 Z-DEPTH ANKLE: RIGHT(landmark 27)={right_ankle_z:.3f}, LEFT(landmark 28)={left_ankle_z:.3f}, diff={abs(right_ankle_z - left_ankle_z):.3f}")
        
        # Si hay diferencia significativa en profundidad (>0.05), priorizar la más cercana
        z_diff = abs(right_ankle_z - left_ankle_z)
        if z_diff > 0.05:
            if right_ankle_z < left_ankle_z:  # Derecha más cerca
                print(f"🎯 PRIMARY_LEG: RIGHT (Z-depth más cercano: {right_ankle_z:.3f} < {left_ankle_z:.3f})")
                return 'RIGHT'
            else:  # Izquierda más cerca
                print(f"🎯 PRIMARY_LEG: LEFT (Z-depth más cercano: {left_ankle_z:.3f} < {right_ankle_z:.3f})")
                return 'LEFT'
        
        print(f"🔍 Z-depth similar, evaluando calidad: RIGHT={right_quality}, LEFT={left_quality}")
        
        # 2. Priorizar por calidad de detección (3 factores)
        if right_quality > left_quality:
            print(f"🎯 PRIMARY_LEG: RIGHT (quality {right_quality} > {left_quality})")
            return 'RIGHT'
        elif left_quality > right_quality:
            print(f"🎯 PRIMARY_LEG: LEFT (quality {left_quality} > {right_quality})")
            return 'LEFT'
        
        # 3. Si calidad igual, priorizar por ángulo válido (no 0)
        if right_angle > 5 and left_angle <= 5:
            print(f"🎯 PRIMARY_LEG: RIGHT (ángulo válido {right_angle})")
            return 'RIGHT'
        elif left_angle > 5 and right_angle <= 5:
            print(f"🎯 PRIMARY_LEG: LEFT (ángulo válido {left_angle})")
            return 'LEFT'
        
        # 4. Si todo igual, priorizar por visibilidad total
        # 🪞 INVERTIDO: landmarks[27] = tobillo DERECHO real, landmarks[28] = tobillo IZQUIERDO real
        right_vis = landmarks[27].visibility if hasattr(landmarks[27], 'visibility') else 0  # ✅ Landmark LEFT = tobillo DERECHO
        left_vis = landmarks[28].visibility if hasattr(landmarks[28], 'visibility') else 0   # ✅ Landmark RIGHT = tobillo IZQUIERDO
        
        print(f"🔍 Visibilidad: RIGHT(landmark 27)={right_vis:.2f}, LEFT(landmark 28)={left_vis:.2f}")
        
        if right_vis > left_vis:
            print(f"🎯 PRIMARY_LEG: RIGHT (visibilidad {right_vis:.2f} > {left_vis:.2f})")
            return 'RIGHT'
        else:
            print(f"🎯 PRIMARY_LEG: LEFT (visibilidad {left_vis:.2f} >= {right_vis:.2f})")
            return 'LEFT'

    def draw_joint_visualization(self, frame, landmarks, angles):
        """
        🦶 VISUALIZACIÓN DE TOBILLOS - ADAPTADA DE TEST_ANKLE_MOVEMENTS.PY Y KNEE_ANALYZER.PY
        🎨 Puntos GRANDES con colores específicos (igual que test)
        📐 Líneas VERDES para pierna/pie (replica test)
        🎯 Solo lado activo en PERFIL, ambos en FRONTAL
        """
        h, w, _ = frame.shape
        
        try:
            pos = angles.get('positions', {})
            if not pos:
                return frame
            
            # 🎯 OBTENER primary_leg Y view_type
            primary_leg = angles.get('primary_leg', 'BOTH')
            view_type = angles.get('view_type', 'PERFIL')
            
            # 🦶 VISUALIZACIÓN SEGÚN VISTA
            
            # ✅ VISTA PERFIL - Solo lado activo (patrón knee)
            if view_type == 'PERFIL' or primary_leg != 'BOTH':
                
                # Determinar qué lado dibujar
                if primary_leg == 'RIGHT':
                    if all(pos.get(key) for key in ['knee_r', 'ankle_r', 'foot_r']):
                        knee_2d = tuple(map(int, pos['knee_r']))
                        ankle_2d = tuple(map(int, pos['ankle_r']))
                        foot_2d = tuple(map(int, pos['foot_r']))
                        angle = angles.get('right_ankle', 0)
                        movement_type = angles.get('right_movement_type', 'NEUTRAL')
                        
                        # 🎨 PUNTOS GRANDES (test líneas 372-374)
                        cv2.circle(frame, knee_2d, 8, (255, 255, 0), -1)      # Cyan - Rodilla
                        cv2.circle(frame, ankle_2d, 10, (255, 0, 255), -1)    # Magenta - Tobillo (vértice)
                        cv2.circle(frame, foot_2d, 8, (0, 255, 255), -1)      # Amarillo - Pie
                        
                        # 🎨 LÍNEAS VERDES (test líneas 376-377)
                        cv2.line(frame, knee_2d, ankle_2d, (0, 255, 0), 4)    # Verde - Pierna
                        cv2.line(frame, ankle_2d, foot_2d, (0, 255, 0), 3)    # Verde - Pie
                        
                        # 📐 ÁNGULO GRANDE (test línea 379-382)
                        cv2.putText(frame, f"{angle:.1f}", 
                                   (ankle_2d[0] + 20, ankle_2d[1] - 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 4)
                        
                        # 📊 TIPO MOVIMIENTO (test línea 384-387)
                        movement_color = (0, 255, 0) if 'NEUTRAL' in movement_type else (0, 165, 255) if 'DORSI' in movement_type else (0, 0, 255)
                        cv2.putText(frame, movement_type, 
                                   (ankle_2d[0] + 20, ankle_2d[1] + 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, movement_color, 2)
                
                elif primary_leg == 'LEFT':
                    if all(pos.get(key) for key in ['knee_l', 'ankle_l', 'foot_l']):
                        knee_2d = tuple(map(int, pos['knee_l']))
                        ankle_2d = tuple(map(int, pos['ankle_l']))
                        foot_2d = tuple(map(int, pos['foot_l']))
                        angle = angles.get('left_ankle', 0)
                        movement_type = angles.get('left_movement_type', 'NEUTRAL')
                        
                        # 🎨 PUNTOS GRANDES (idéntico a RIGHT)
                        cv2.circle(frame, knee_2d, 8, (255, 255, 0), -1)      # Cyan - Rodilla
                        cv2.circle(frame, ankle_2d, 10, (255, 0, 255), -1)    # Magenta - Tobillo
                        cv2.circle(frame, foot_2d, 8, (0, 255, 255), -1)      # Amarillo - Pie
                        
                        # 🎨 LÍNEAS VERDES (idéntico a RIGHT)
                        cv2.line(frame, knee_2d, ankle_2d, (0, 255, 0), 4)    # Verde - Pierna
                        cv2.line(frame, ankle_2d, foot_2d, (0, 255, 0), 3)    # Verde - Pie
                        
                        # 📐 ÁNGULO GRANDE
                        cv2.putText(frame, f"{angle:.1f}", 
                                   (ankle_2d[0] - 80, ankle_2d[1] - 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 4)
                        
                        # 📊 TIPO MOVIMIENTO
                        movement_color = (0, 255, 0) if 'NEUTRAL' in movement_type else (0, 165, 255) if 'DORSI' in movement_type else (0, 0, 255)
                        cv2.putText(frame, movement_type, 
                                   (ankle_2d[0] - 150, ankle_2d[1] + 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, movement_color, 2)
            
            # ✅ VISTA FRONTAL - Ambos lados (patrón knee)
            elif view_type == 'FRONTAL' or primary_leg == 'BOTH':
                
                # 🦶 TOBILLO IZQUIERDO
                if all(pos.get(key) for key in ['knee_l', 'ankle_l', 'foot_l']):
                    left_knee_2d = tuple(map(int, pos['knee_l']))
                    left_ankle_2d = tuple(map(int, pos['ankle_l']))
                    left_foot_2d = tuple(map(int, pos['foot_l']))
                    left_angle = angles.get('left_ankle', 0)
                    left_state = angles.get('left_movement_type', 'NEUTRAL')
                    
                    # 🎨 PUNTOS GRANDES
                    cv2.circle(frame, left_knee_2d, 8, (255, 255, 0), -1)      # Cyan - Rodilla
                    cv2.circle(frame, left_ankle_2d, 10, (255, 0, 255), -1)    # Magenta - Tobillo
                    cv2.circle(frame, left_foot_2d, 8, (0, 255, 255), -1)      # Amarillo - Pie
                    
                    # 🎨 LÍNEAS VERDES
                    cv2.line(frame, left_knee_2d, left_ankle_2d, (0, 255, 0), 4)   # Verde - Pierna
                    cv2.line(frame, left_ankle_2d, left_foot_2d, (0, 255, 0), 3)   # Verde - Pie
                    
                    # 📐 ÁNGULO
                    cv2.putText(frame, f"{left_angle:.1f}", 
                               (left_ankle_2d[0] - 80, left_ankle_2d[1] - 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 255, 255), 3)
                    
                    # 📊 ESTADO
                    left_color = (0, 255, 0) if 'NEUTRAL' in left_state else (0, 165, 255) if 'DORSI' in left_state else (0, 0, 255)
                    cv2.putText(frame, left_state, 
                               (left_ankle_2d[0] - 70, left_ankle_2d[1] + 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, left_color, 2)
                
                # 🦶 TOBILLO DERECHO
                if all(pos.get(key) for key in ['knee_r', 'ankle_r', 'foot_r']):
                    right_knee_2d = tuple(map(int, pos['knee_r']))
                    right_ankle_2d = tuple(map(int, pos['ankle_r']))
                    right_foot_2d = tuple(map(int, pos['foot_r']))
                    right_angle = angles.get('right_ankle', 0)
                    right_state = angles.get('right_movement_type', 'NEUTRAL')
                    
                    # 🎨 PUNTOS GRANDES
                    cv2.circle(frame, right_knee_2d, 8, (255, 255, 0), -1)     # Cyan - Rodilla
                    cv2.circle(frame, right_ankle_2d, 10, (255, 0, 255), -1)   # Magenta - Tobillo
                    cv2.circle(frame, right_foot_2d, 8, (0, 255, 255), -1)     # Amarillo - Pie
                    
                    # 🎨 LÍNEAS VERDES
                    cv2.line(frame, right_knee_2d, right_ankle_2d, (0, 255, 0), 4) # Verde - Pierna
                    cv2.line(frame, right_ankle_2d, right_foot_2d, (0, 255, 0), 3) # Verde - Pie
                    
                    # 📐 ÁNGULO
                    cv2.putText(frame, f"{right_angle:.1f}", 
                               (right_ankle_2d[0] + 30, right_ankle_2d[1] - 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 255, 255), 3)
                    
                    # 📊 ESTADO
                    right_color = (0, 255, 0) if 'NEUTRAL' in right_state else (0, 165, 255) if 'DORSI' in right_state else (0, 0, 255)
                    cv2.putText(frame, right_state, 
                               (right_ankle_2d[0] + 20, right_ankle_2d[1] + 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, right_color, 2)
            
            # 📊 INFORMACIÓN SUPERIOR (simple, sin PIL)
            cv2.putText(frame, f"Vista: {view_type} | Lado: {primary_leg}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
        except Exception as e:
            cv2.putText(frame, f"ERROR VISUALIZACION: {str(e)[:40]}", (10, 130), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        return frame

    def _select_primary_foot(self, right_result, left_result, orientation):
        """🎯 Seleccionar pie/tobillo principal según orientación (igual que knee/hip)"""
        
        right_valid = right_result['status'] == 'VALID'
        left_valid = left_result['status'] == 'VALID'
        
        if orientation == "SAGITAL":
            # En sagital, priorizar pie más visible (evitar confusión)
            if right_valid and not left_valid:
                return "RIGHT"
            elif left_valid and not right_valid:
                return "LEFT"
            elif right_valid and left_valid:
                return "RIGHT" if right_result['quality'] >= left_result['quality'] else "LEFT"
            else:
                return "NONE"
        else:
            # En frontal/transversal, mostrar ambos si están disponibles
            return "BOTH" if right_valid and left_valid else ("RIGHT" if right_valid else ("LEFT" if left_valid else "NONE"))

    def _interpret_ankle_angle(self, angle):
        """
        🔍 Interpretar ángulo de tobillo (POST-CALIBRACIÓN)
        Neutral = 90° | Dorsiflex >100° | Plantiflex <80°
        """
        if angle >= 100:
            return "DORSIFLEX"  # Punta hacia arriba (>10° desde neutral)
        elif angle <= 80:
            return "PLANTIFLEX" # Punta hacia abajo (<10° desde neutral)
        else:
            return "NEUTRAL"    # Rango neutral: 80-100° (±10° tolerancia)

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
            #cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 
            #           font_size/30, color, 2)
            return frame

    def reset_filters(self):
        """🔄 Resetear filtros temporales"""
        try:
            if hasattr(self, 'angle_filters'):
                self.angle_filters.clear()
                print("🔄 Filtros de tobillo reseteados")
        except Exception as e:
            print(f"⚠️ Error reseteando filtros: {e}")