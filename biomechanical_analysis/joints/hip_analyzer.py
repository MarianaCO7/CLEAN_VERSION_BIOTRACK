"""
🦴 ANALIZADOR DE CADERA COMPLETO
🎯 Heredando toda la funcionalidad base + específico de cadera
"""

import sys
import os
import json  # 🆕 Para cargar exercises.json
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import numpy as np
import cv2
import math
from core.base_analyzer import BaseJointAnalyzer  # ✅ VERIFICAR ESTA LÍNEA
from core.orientation_detector import AdaptiveOrientationDetector
from core.fixed_references import FixedSpatialReferences  # 🆕 MÉTODO CIENTÍFICO

class HipAnalyzer(BaseJointAnalyzer):
    """
    🦴 ANALIZADOR ESPECÍFICO DE CADERA
    🎯 Flexión/Extensión/Abducción (múltiples planos)
    """
    
    def __init__(self):
        super().__init__("Hip")
        
        # 🆕 MEDIAPIPE EXPLICIT SETUP (garantizar que funcione)
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
            print("✅ MediaPipe inicializado correctamente para cadera")
            
        except Exception as e:
            print(f"❌ Error inicializando MediaPipe: {e}")
            raise
        
        self.orientation_detector = AdaptiveOrientationDetector()
        # 🆕 ESTABILIDAD DE ORIENTACIÓN (como codo)
        self.orientation_history = []
        self.current_stable_orientation = "FRONTAL"
        self.orientation_change_cooldown = 0
        
        # � ORIENTACIÓN DE CÁMARA (del JSON de ejercicio - FIX 4 como elbow)
        self.current_camera_orientation = "SAGITAL"  # Default: SAGITAL para flexion
        
        # �🎯 SOPORTE MULTI-EJERCICIO
        self.current_exercise = "flexion"  # Default exercise
    
    def set_current_exercise(self, exercise_type: str):
        """
        Configura el ejercicio actual para el análisis
        🆕 FIX 4: Ahora lee camera_orientation desde exercises.json
        
        Args:
            exercise_type: Tipo de ejercicio ('flexion', 'abduction', 'adduction')
        """
        valid_exercises = ['flexion', 'extension', 'abduction', 'adduction']
        if exercise_type in valid_exercises:
            self.current_exercise = exercise_type
            print(f"🎯 Ejercicio de cadera configurado: {exercise_type}")
            
            # 🆕 FIX 4: CARGAR camera_orientation desde JSON (como elbow)
            if not hasattr(self, 'exercise_configs'):
                # Cargar exercises.json una sola vez
                config_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'biomechanical_web_interface', 'config', 'exercises.json'
                )
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.exercise_configs = data['segments']['hip']['exercises']
                except Exception as e:
                    print(f"⚠️ Error cargando exercises.json: {e}")
                    self.exercise_configs = {}
            
            # 🆕 OBTENER camera_orientation del ejercicio actual
            if exercise_type in self.exercise_configs:
                exercise_data = self.exercise_configs[exercise_type]
                self.current_camera_orientation = exercise_data.get('camera_orientation', 'SAGITAL')
                print(f"📷 Camera orientation para {exercise_type}: {self.current_camera_orientation}")
            else:
                # Defaults según tipo de ejercicio
                if exercise_type in ['abduction', 'adduction']:
                    self.current_camera_orientation = 'FRONTAL'
                else:
                    self.current_camera_orientation = 'SAGITAL'
                print(f"⚠️ No se encontró config para {exercise_type}, usando '{self.current_camera_orientation}' por defecto")
        else:
            print(f"⚠️ Ejercicio inválido: {exercise_type}. Usando flexion por defecto.")
            self.current_exercise = "flexion"
            self.current_camera_orientation = 'SAGITAL'
        
        # 🎯 EJERCICIOS ESPECÍFICOS DE CADERA
        self.exercise_types = {
            "hip_flexion": "Flexión de Cadera",
            "hip_extension": "Extensión de Cadera", 
            "hip_abduction": "Abducción de Cadera (lateral)",
            "hip_adduction": "Aducción de Cadera",
            "hip_general": "Movimiento General de Cadera"
        }
        
        # 📊 RANGOS NORMATIVOS DE CADERA
        self.normal_ranges = {
            "hip_flexion": {"min": 0, "max": 120, "functional": 90},
            "hip_extension": {"min": 0, "max": 30, "functional": 20},
            "hip_abduction": {"min": 0, "max": 45, "functional": 30},
            "hip_adduction": {"min": 0, "max": 30, "functional": 15}
        }
    
    def get_required_landmarks(self):
        """🎯 Puntos requeridos para análisis de cadera"""
        return {
            "essential": [23, 25, 27],     # Cadera, rodilla, tobillo (izquierdo)
            "alternative": [24, 26, 28],   # Cadera, rodilla, tobillo (derecho)
            "support": [11, 12],           # Hombros para referencia corporal
            "recommended": [23, 24, 25, 26, 27, 28]  # Ambas piernas
        }
    
    def check_required_points_visible(self, landmarks):
        """✅ Verificar visibilidad - COMPATIBLE CON NUEVO SISTEMA"""
        
        if not landmarks or len(landmarks) < 29:
            return False
        
        # 🔍 DETECCIÓN DE EJERCICIOS FRONTALES
        is_frontal_exercise = self.current_exercise in ['abduction', 'abduccion', 'adduction', 'aduccion', 'internal_rotation', 'rotacion_interna']
        
        # 🎯 USAR DETECCIÓN DEL TEST (no el detector viejo) - 🆕 AHORA 5 VALORES
        try:
            view_type, detected_side, confidence, orientation, facing_direction = self.detect_side_and_visibility(landmarks)
        except Exception as e:
            print(f"⚠️ Error en detect_side_and_visibility: {e}")
            return False
        
        # 🎯 UMBRALES PERMISIVOS
        if view_type == "SAGITAL":  # ✅ De perfil = vista sagital
            visibility_threshold = 0.3
            min_points_required = 2  # Solo 2 de 3 puntos (cadera, rodilla mínimo)
            # 🔇 CACHE: Solo imprimir si cambia el tipo de check
            if not hasattr(self, '_last_check_type') or self._last_check_type != 'SAGITAL':
                print(f"🎯 [HIP check_points] SAGITAL (perfil) - Umbral={visibility_threshold}, Ejercicio={self.current_exercise}")
                self._last_check_type = 'SAGITAL'
        else:  # FRONTAL
            # 🆕 SI ES EJERCICIO FRONTAL, umbral más bajo
            visibility_threshold = 0.35 if is_frontal_exercise else 0.4
            min_points_required = 2
            # 🔇 CACHE: Solo imprimir si cambia el tipo de check
            if not hasattr(self, '_last_check_type') or self._last_check_type != 'FRONTAL':
                print(f"🎯 [HIP check_points] FRONTAL - Umbral={visibility_threshold}, IsFrontalEx={is_frontal_exercise}")
                self._last_check_type = 'FRONTAL'
        
        # 📊 VERIFICAR PUNTOS ESENCIALES (cadera + rodilla + hombro)
        # Si es SAGITAL (perfil), solo verificar el lado visible
        if view_type == "SAGITAL" and detected_side:
            if detected_side == 'left':
                # Verificar pierna izquierda [23=cadera, 25=rodilla] + [11=hombro]
                points_to_check = [23, 25, 11]
            else:  # 'right'
                # Verificar pierna derecha [24=cadera, 26=rodilla] + [12=hombro]
                points_to_check = [24, 26, 12]
            
            valid_points = sum(1 for idx in points_to_check 
                             if idx < len(landmarks) and landmarks[idx].visibility > visibility_threshold)
            
            is_valid = valid_points >= min_points_required
            # 🔇 CACHE: Solo imprimir si cambia el resultado de validación
            cache_key = f"SAGITAL_{detected_side}_{is_valid}_{valid_points}"
            if not hasattr(self, '_last_sagital_result') or self._last_sagital_result != cache_key:
                print(f"✅ [HIP] SAGITAL (perfil) {detected_side.upper()}: {valid_points}/3 → {'✓' if is_valid else '✗'}")
                self._last_sagital_result = cache_key
            
        else:  # FRONTAL - verificar ambas piernas
            left_valid = sum(1 for idx in [23, 25, 11]
                           if idx < len(landmarks) and landmarks[idx].visibility > visibility_threshold)
            right_valid = sum(1 for idx in [24, 26, 12]
                            if idx < len(landmarks) and landmarks[idx].visibility > visibility_threshold)
            
            # Al menos UNA pierna debe tener puntos suficientes
            is_valid = (left_valid >= min_points_required) or (right_valid >= min_points_required)
            # 🔇 CACHE: Solo imprimir si cambia el resultado
            cache_key = f"FRONTAL_{is_valid}_{left_valid}_{right_valid}"
            if not hasattr(self, '_last_frontal_result') or self._last_frontal_result != cache_key:
                print(f"✅ [HIP] FRONTAL: L={left_valid}/3, R={right_valid}/3 → {'✓' if is_valid else '✗'}")
                self._last_frontal_result = cache_key
        
        return is_valid
    
    def detect_side_and_visibility(self, landmarks):
        """
        🎯 DETECCIÓN DE ORIENTACIÓN Y LADO VISIBLE (del test_hip_movements.py)
        
        Detecta qué lado del cuerpo está visible y hacia dónde mira la persona
        También determina si está de SAGITAL (perfil) o FRONTAL
        
        Returns:
            tuple: (view_type, side, confidence, orientation, facing_direction)  # 🆕 5 VALORES
                - view_type: "SAGITAL" (perfil) o "FRONTAL"
                - side: 'left'/'right' (solo en SAGITAL), None (en FRONTAL)
                - confidence: valor de confianza (0-1)
                - orientation: descripción textual de la orientación
                - facing_direction: "FRONTAL"/"DERECHA"/"IZQUIERDA" (mirada del usuario)
        """
        # Obtener puntos clave usando índices directos
        left_shoulder = landmarks[11]   # LEFT_SHOULDER
        right_shoulder = landmarks[12]  # RIGHT_SHOULDER
        left_hip = landmarks[23]        # LEFT_HIP
        right_hip = landmarks[24]       # RIGHT_HIP
        nose = landmarks[0]             # NOSE
        
        # Calcular visibilidad de cada lado
        left_visibility = (left_shoulder.visibility + left_hip.visibility) / 2
        right_visibility = (right_shoulder.visibility + right_hip.visibility) / 2
        
        # Calcular distancia entre hombros (en coordenadas normalizadas)
        shoulder_distance = abs(right_shoulder.x - left_shoulder.x)
        
        # Calcular distancia entre caderas
        hip_distance = abs(right_hip.x - left_hip.x)
        
        # Promedio de visibilidad y distancias
        avg_visibility = (left_visibility + right_visibility) / 2
        avg_distance = (shoulder_distance + hip_distance) / 2
        
        # 🆕 CALCULAR FACING DIRECTION (hacia dónde mira - sistema moderno)
        nose_x = nose.x
        shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2
        
        # Determinar facing_direction basado en posición de nariz respecto a centro de hombros
        if avg_distance > 0.10 and avg_visibility > 0.55:  # 🔧 AJUSTE: 0.12→0.10, 0.6→0.55 (más permisivo para FRONTAL)
            # Mirando de frente (ambos lados visibles)
            facing_direction = "FRONTAL"
        elif nose_x < shoulder_center_x - 0.04:  # 🔧 AJUSTE: 0.05→0.04 (detectar PERFIL más rápido)
            # Nariz a la izquierda del centro → mirando izquierda
            facing_direction = "IZQUIERDA"
        elif nose_x > shoulder_center_x + 0.04:  # 🔧 AJUSTE: 0.05→0.04 (detectar PERFIL más rápido)
            # Nariz a la derecha del centro → mirando derecha
            facing_direction = "DERECHA"
        else:
            # Transición o ambiguo → usar visibilidad como fallback
            facing_direction = "DERECHA" if right_visibility > left_visibility else "IZQUIERDA"
        
        # Determinar si está de FRENTE o PERFIL
        if avg_distance > 0.10 and avg_visibility > 0.55 and left_visibility > 0.45 and right_visibility > 0.45:  # 🔧 AJUSTE: 0.12→0.10, 0.6→0.55, 0.5→0.45
            # Vista FRONTAL - Para análisis de abducción
            view_type = "FRONTAL"
            side = None
            confidence = avg_visibility
            orientation = "de frente (Análisis de ABDUCCIÓN)"
        else:
            # Vista de PERFIL - Para análisis de flexión/extensión
            view_type = "SAGITAL"  # ✅ CORREGIDO: Usar "SAGITAL" (consistente con otros analyzers)
            
            # Determinar qué pierna está más visible
            if left_visibility > right_visibility:
                side = 'left'
                confidence = left_visibility
                orientation = "mirando izquierda" if nose_x < shoulder_center_x else "mirando derecha"
            else:
                side = 'right'
                confidence = right_visibility
                orientation = "mirando derecha" if nose_x > shoulder_center_x else "mirando izquierda"
        
        # 🆕 RETORNAR 5 VALORES (lección aprendida del codo)
        return view_type, side, confidence, orientation, facing_direction
    
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
            - Ejercicio FRONTAL (abducción) → requiere facing='FRONTAL'
            - Ejercicio SAGITAL (flexión/extensión) → requiere facing='IZQUIERDA' o 'DERECHA'
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
                    print(f"⏱️ [HIP] Timeout {force_accept_after_seconds}s alcanzado - ACEPTANDO orientación automáticamente")
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
                print(f"🧭 [HIP validate_orientation_by_facing]")
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
            print(f"❌ Error validando orientación HIP: {e}")
            return False
    
    def calculate_flexion_extension_angle(self, hip, knee, shoulder, side):
        """
        📐 MÉTODO CIENTÍFICO: Calcular ángulo de FLEXIÓN/EXTENSIÓN de cadera en vista SAGITAL
        🎯 Mide ángulo entre MUSLO y EJE VERTICAL (similar a goniómetro)
        
        Sistema de ángulos:
        - Vector de referencia: Línea vertical desde hombro hacia cadera
        - Vector del muslo: De cadera a rodilla
        - 0° = Pierna vertical hacia abajo (posición neutra)
        - Positivo hacia adelante = FLEXIÓN
        - Positivo hacia atrás = EXTENSIÓN
        
        Args:
            hip: tuple (x, y) coordenadas de la cadera
            knee: tuple (x, y) coordenadas de la rodilla
            shoulder: tuple (x, y) coordenadas del hombro
            side: 'left' o 'right' (afecta dirección del ángulo)
        
        Returns:
            float: Ángulo en grados (+ = flexión, - = extensión)
        """
        # Vector vertical de referencia (hombro → cadera)
        reference_vector = np.array([hip[0] - shoulder[0], hip[1] - shoulder[1]])
        
        # Vector del muslo (cadera → rodilla)
        thigh_vector = np.array([knee[0] - hip[0], knee[1] - hip[1]])
        
        # Normalizar vectores
        ref_norm = np.linalg.norm(reference_vector)
        thigh_norm = np.linalg.norm(thigh_vector)
        
        if ref_norm == 0 or thigh_norm == 0:
            return 0
        
        reference_normalized = reference_vector / ref_norm
        thigh_normalized = thigh_vector / thigh_norm
        
        # Calcular ángulo base
        dot_product = np.dot(reference_normalized, thigh_normalized)
        dot_product = np.clip(dot_product, -1.0, 1.0)
        angle_magnitude = np.degrees(np.arccos(dot_product))
        
        # 🎯 DETERMINAR DIRECCIÓN (flexión vs extensión) con producto cruz
        cross_product = reference_vector[0] * thigh_vector[1] - reference_vector[1] * thigh_vector[0]
        
        # Para vista de perfil: positivo hacia adelante = flexión
        if side == 'left':
            angle = angle_magnitude if cross_product > 0 else -angle_magnitude
        else:
            angle = angle_magnitude if cross_product < 0 else -angle_magnitude
        
        return angle
    
    def calculate_abduction_angle(self, hip, hip_opposite, knee):
        """
        📐 MÉTODO CIENTÍFICO: Calcular ángulo de ABDUCCIÓN de cadera en vista FRONTAL
        🎯 Mide ángulo entre MUSLO y LÍNEA HORIZONTAL (entre caderas)
        
        Sistema de ángulos:
        - 0° = Pierna vertical (pegada al cuerpo)
        - 45° = Abducción funcional
        - 90° = Pierna completamente horizontal
        
        Args:
            hip: tuple (x, y) coordenadas de la cadera
            hip_opposite: tuple (x, y) coordenadas de la cadera opuesta
            knee: tuple (x, y) coordenadas de la rodilla
        
        Returns:
            float: Ángulo en grados (0° = vertical, 90° = horizontal)
        """
        # Vector horizontal de referencia (cadera opuesta → cadera)
        horizontal_vector = np.array([hip[0] - hip_opposite[0], hip[1] - hip_opposite[1]])
        
        # Vector del muslo (cadera → rodilla)
        thigh_vector = np.array([knee[0] - hip[0], knee[1] - hip[1]])
        
        # Normalizar vectores
        horiz_norm = np.linalg.norm(horizontal_vector)
        thigh_norm = np.linalg.norm(thigh_vector)
        
        if horiz_norm == 0 or thigh_norm == 0:
            return 0
        
        horizontal_normalized = horizontal_vector / horiz_norm
        thigh_normalized = thigh_vector / thigh_norm
        
        # Calcular ángulo
        dot_product = np.dot(horizontal_normalized, thigh_normalized)
        dot_product = np.clip(dot_product, -1.0, 1.0)
        
        # Calcular ángulo respecto a horizontal, convertir a vertical
        angle_from_horizontal = np.degrees(np.arccos(abs(dot_product)))
        
        # Convertir a ángulo desde vertical (0° = pierna vertical)
        angle_from_vertical = 90 - angle_from_horizontal
        
        return abs(angle_from_vertical)
    
    def calculate_joint_angles(self, landmarks, frame_shape):
        """
        📐 CÁLCULO DE ÁNGULOS DE CADERA (ADAPTADO DEL TEST)
        
        🎯 LÓGICA DEL TEST_HIP_MOVEMENTS.PY:
        - Detecta orientación (SAGITAL vs FRONTAL) con detect_side_and_visibility()
        - SAGITAL (perfil): Calcula flexión/extensión con calculate_flexion_extension_angle()
        - FRONTAL: Calcula abducción bilateral con calculate_abduction_angle()
        - Retorna raw_right, raw_left para ROM tracking inteligente
        """
        
        # 🔇 CACHE: Solo imprimir en primera llamada (se ejecuta 30 veces/segundo)
        if not hasattr(self, '_calculate_angles_logged'):
            print(f"🔍 [HIP calculate_joint_angles] Primera llamada - landmarks: {len(landmarks) if landmarks else 0}")
            self._calculate_angles_logged = True
        
        if not landmarks or len(landmarks) < 29:
            return {
                'right_hip': 0,
                'left_hip': 0,
                'raw_right': 0,
                'raw_left': 0,
                'positions': {},
                'orientation_info': {'orientation': 'DESCONOCIDO', 'view_type': None, 'detected_side': None},
                'valid': False
            }
        
        h, w = frame_shape[:2]
        
        # 🎯 FASE 1: DETECCIÓN DE ORIENTACIÓN Y LADO VISIBLE (del test) - 🆕 5 VALORES
        view_type, detected_side, confidence, orientation, facing_direction = self.detect_side_and_visibility(landmarks)
        
        # 🔇 CACHE: Solo imprimir cuando cambia el estado (evitar 30 prints/segundo)
        cache_key = f"{view_type}_{detected_side}_{facing_direction}"
        if not hasattr(self, '_last_orientation_log') or self._last_orientation_log != cache_key:
            print(f"🧭 [HIP] View: {view_type}, Side: {detected_side}, Facing: {facing_direction}")
            self._last_orientation_log = cache_key
        
        # 📍 FASE 2: EXTRAER PUNTOS CLAVE
        # Pierna derecha
        hip_r = landmarks[24]  # RIGHT_HIP
        knee_r = landmarks[26]  # RIGHT_KNEE
        shoulder_r = landmarks[12]  # RIGHT_SHOULDER
        
        # Pierna izquierda
        hip_l = landmarks[23]  # LEFT_HIP
        knee_l = landmarks[25]  # LEFT_KNEE
        shoulder_l = landmarks[11]  # LEFT_SHOULDER
        
        # Convertir a coordenadas de píxeles
        hip_r_px = (int(hip_r.x * w), int(hip_r.y * h))
        knee_r_px = (int(knee_r.x * w), int(knee_r.y * h))
        shoulder_r_px = (int(shoulder_r.x * w), int(shoulder_r.y * h))
        
        hip_l_px = (int(hip_l.x * w), int(hip_l.y * h))
        knee_l_px = (int(knee_l.x * w), int(knee_l.y * h))
        shoulder_l_px = (int(shoulder_l.x * w), int(shoulder_l.y * h))
        
        # 🎯 FASE 3: CALCULAR ÁNGULOS SEGÚN ORIENTACIÓN
        if view_type == "PERFIL":
            # 📐 PERFIL: Flexión/Extensión con hombro como referencia vertical
            if detected_side == 'left':
                # Lado izquierdo visible → calcular ángulo izquierdo
                angle_left_raw = self.calculate_flexion_extension_angle(
                    hip_l_px, knee_l_px, shoulder_l_px, 'left'
                )
                angle_right_raw = 0  # Lado no visible
            else:  # detected_side == 'right'
                # Lado derecho visible → calcular ángulo derecho
                angle_right_raw = self.calculate_flexion_extension_angle(
                    hip_r_px, knee_r_px, shoulder_r_px, 'right'
                )
                angle_left_raw = 0  # Lado no visible
        
        else:  # view_type == "FRONTAL"
            # 🔵 FRONTAL: Abducción bilateral (ambas piernas)
            angle_right_raw = self.calculate_abduction_angle(hip_r_px, hip_l_px, knee_r_px)
            angle_left_raw = self.calculate_abduction_angle(hip_l_px, hip_r_px, knee_l_px)
        
        # 🔇 CACHE: Solo imprimir cuando los ángulos cambian significativamente (>2°)
        if not hasattr(self, '_last_angles_log'):
            self._last_angles_log = (0, 0)
        
        angle_change = abs(angle_right_raw - self._last_angles_log[0]) + abs(angle_left_raw - self._last_angles_log[1])
        if angle_change > 4:  # Cambio total > 4° (2° por lado)
            print(f"📐 [HIP] RAW - R: {angle_right_raw:.1f}°, L: {angle_left_raw:.1f}°")
            self._last_angles_log = (angle_right_raw, angle_left_raw)
        
        # 📊 FASE 4: APLICAR FILTROS TEMPORALES
        filtered_angle_r = self.apply_temporal_filter(angle_right_raw, 'right_hip')
        filtered_angle_l = self.apply_temporal_filter(angle_left_raw, 'left_hip')
        
        # � FASE 5: ESTRUCTURAR RESULTADO (compatible con handler)
        angles = {
            # Ángulos filtrados (para visualización suave)
            'right_hip': filtered_angle_r,
            'left_hip': filtered_angle_l,
            
            # Ángulos crudos (para ROM tracking preciso)
            'raw_right': angle_right_raw,
            'raw_left': angle_left_raw,
            
            # Posiciones de puntos clave (para visualización)
            'positions': {
                'hip_r': hip_r_px,
                'knee_r': knee_r_px,
                'shoulder_r': shoulder_r_px,
                'hip_l': hip_l_px,
                'knee_l': knee_l_px,
                'shoulder_l': shoulder_l_px
            },
            
            # Información de orientación (para handler)
            'orientation_info': {
                'orientation': view_type,  # "PERFIL" o "FRONTAL"
                'view_type': view_type,
                'detected_side': detected_side,  # 'left'/'right' (PERFIL) o None (FRONTAL)
                'confidence': confidence,
                'description': orientation
            },
            
            # Validez del análisis
            'valid': True
        }
        
        return angles
    
    # ===========================================================================
    # 🔴 MÉTODOS ANTIGUOS DEPRECADOS (NO USAR - Reemplazados por test_hip_movements.py)
    # ===========================================================================
    #
    # NOTA: Los siguientes métodos fueron reemplazados por la lógica directa del test
    # que está integrada en calculate_joint_angles() arriba. 
    #
    # ✅ MÉTODOS ACTIVOS (del test_hip_movements.py):
    #    - detect_side_and_visibility()  → Usado en calculate_joint_angles()
    #    - calculate_flexion_extension_angle()  → Usado en calculate_joint_angles()
    #    - calculate_abduction_angle()  → Usado en calculate_joint_angles()
    #
    # ❌ MÉTODOS DEPRECADOS (comentados abajo):
    #    - _analyze_single_leg()  → Lógica integrada en calculate_joint_angles()
    #    - _select_primary_leg()  → Lógica integrada en calculate_joint_angles()
    #    - _get_stable_orientation()  → Reemplazado por detect_side_and_visibility()
    #    - _calculate_hip_angle_frontal()  → Reemplazado por calculate_abduction_angle()
    #    - _calculate_hip_angle_sagital()  → Reemplazado por calculate_flexion_extension_angle()
    #    - _detect_abduction()  → Ya no necesario con nuevo sistema
    #
    # ===========================================================================
    
    # def _analyze_single_leg(self, landmarks, leg_side, w, h, orientation):
    #     """🦴 Analizar UNA pierna - CON DETECCIÓN DE ABDUCCIÓN"""
    #     pass  # Código comentado - ver arriba para lógica integrada
    
    # def _select_primary_leg(self, right_result, left_result, orientation):
    #     """🎯 Seleccionar la pierna principal según orientación"""
    #     pass  # Código comentado - ver arriba para lógica integrada
    
    # def _get_stable_orientation(self, landmarks):
    #     """🧭 Orientación ESTABLE - copiado del sistema de codos"""
    #     pass  # Código comentado - ahora usamos detect_side_and_visibility()
    
    def _get_default_result(self):
        """📊 Resultado por defecto cuando no hay datos suficientes"""
        return {
            'right_hip': 0, 'left_hip': 0, 'raw_right': 0, 'raw_left': 0,
            'positions': {k: None for k in ['hip_r', 'knee_r', 'shoulder_r', 'ankle_r', 'hip_l', 'knee_l', 'shoulder_l', 'ankle_l']}, # ✅ INCLUIR ankle
            'orientation_info': {'orientation': 'UNKNOWN'},
            'primary_leg': 'NONE', 'right_leg_quality': 0, 'left_leg_quality': 0
        }
    
    def draw_joint_visualization(self, frame, landmarks, angles):
        """
        🎨 VISUALIZACIÓN ADAPTADA DE test_hip_movements.py
        
        🎯 PATRÓN SHOULDER:
        - Vectores como en test (hombro→cadera, cadera→rodilla)
        - Sin puntos de cara (solo landmarks corporales)
        - Arcos mantenidos (funcionan bien)
        - Filtrado por active_side (según orientación)
        """
        # ✅ FIX: Validar frame antes de acceder a .shape
        if frame is None:
            print(f"⚠️ HIP draw_joint_visualization: frame is None, retornando None")
            return None
        
        h, w, _ = frame.shape
        
        try:
            # 🎯 OBTENER INFORMACIÓN DE ORIENTACIÓN
            orientation_info = angles.get('orientation_info', {})
            view_type = orientation_info.get('view_type', 'FRONTAL')
            detected_side = orientation_info.get('detected_side', None)
            
            # 📍 OBTENER POSICIONES
            pos = angles.get('positions', {})
            if not pos:
                return frame
            
            # 🎯 DETERMINAR QUÉ PIERNAS MOSTRAR (como shoulder)
            if view_type == "PERFIL":
                # PERFIL: Solo mostrar lado visible
                show_right = (detected_side == 'right')
                show_left = (detected_side == 'left')
            else:
                # FRONTAL: Mostrar ambas piernas
                show_right = True
                show_left = True
            
            # =============================================================================
            # 🎨 FASE 1: DIBUJAR VECTORES (como test_hip_movements.py)
            # =============================================================================
            
            # 📐 CONVERTIR A COORDENADAS INT
            shoulder_r = tuple(map(int, pos['shoulder_r']))
            hip_r = tuple(map(int, pos['hip_r']))
            knee_r = tuple(map(int, pos['knee_r']))
            
            shoulder_l = tuple(map(int, pos['shoulder_l']))
            hip_l = tuple(map(int, pos['hip_l']))
            knee_l = tuple(map(int, pos['knee_l']))
            
            # ✅ PIERNA DERECHA - Solo si está activa
            if show_right:
                # 🔵 PUNTOS CLAVE (como test)
                cv2.circle(frame, hip_r, 10, (255, 0, 255), -1)      # Magenta - Cadera (vértice)
                cv2.circle(frame, knee_r, 8, (0, 255, 255), -1)      # Amarillo - Rodilla
                cv2.circle(frame, shoulder_r, 8, (255, 255, 0), -1)  # Cyan - Hombro
                
                # 📐 VECTORES (como test)
                cv2.line(frame, shoulder_r, hip_r, (200, 200, 200), 2)  # Gris - Referencia vertical
                cv2.line(frame, hip_r, knee_r, (0, 255, 0), 4)          # Verde - Muslo
            
            # ✅ PIERNA IZQUIERDA - Solo si está activa
            if show_left:
                # 🔵 PUNTOS CLAVE (como test)
                cv2.circle(frame, hip_l, 10, (255, 0, 255), -1)      # Magenta - Cadera (vértice)
                cv2.circle(frame, knee_l, 8, (0, 255, 255), -1)      # Amarillo - Rodilla
                cv2.circle(frame, shoulder_l, 8, (255, 255, 0), -1)  # Cyan - Hombro
                
                # 📐 VECTORES (como test)
                cv2.line(frame, shoulder_l, hip_l, (200, 200, 200), 2)  # Gris - Referencia vertical
                cv2.line(frame, hip_l, knee_l, (0, 255, 0), 4)          # Verde - Muslo
            
            # ✅ LÍNEA HORIZONTAL ENTRE CADERAS (FRONTAL - como test)
            if view_type == "FRONTAL":
                cv2.line(frame, hip_l, hip_r, (200, 200, 200), 2)  # Gris - Línea horizontal
            
            # =============================================================================
            # � FASE 2: ARCOS DE ÁNGULOS (mantener código actual - funciona bien)
            # =============================================================================
            
            # PIERNA DERECHA - Solo si está activa
            if show_right and all(pos.get(key) is not None for key in ['hip_r', 'knee_r', 'shoulder_r']):
                frame = self.draw_angle_arc_advanced(
                    frame, pos['hip_r'], pos['shoulder_r'], pos['knee_r'], 
                    angles['right_hip'], 30
                )
            
            # PIERNA IZQUIERDA - Solo si está activa
            if show_left and all(pos.get(key) is not None for key in ['hip_l', 'knee_l', 'shoulder_l']):
                frame = self.draw_angle_arc_advanced(
                    frame, pos['hip_l'], pos['shoulder_l'], pos['knee_l'], 
                    angles['left_hip'], 30
                )
            
            # =============================================================================
            # 📐 FASE 3: TEXTO DE ÁNGULOS (como test)
            # =============================================================================
            
            # � ÁNGULO DERECHO - Solo si está activo
            if show_right:
                angle_value_r = angles['right_hip']
                angle_text_r = f"{abs(angle_value_r):.1f}"  # abs() para display positivo
                cv2.putText(frame, angle_text_r, 
                           (hip_r[0] + 20, hip_r[1] - 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 4)
            
            # 🎯 ÁNGULO IZQUIERDO - Solo si está activo
            if show_left:
                angle_value_l = angles['left_hip']
                angle_text_l = f"{abs(angle_value_l):.1f}"  # abs() para display positivo
                cv2.putText(frame, angle_text_l, 
                           (hip_l[0] + 20, hip_l[1] - 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 4)
            
            # =============================================================================
            # 📊 FASE 4: INFORMACIÓN GENERAL (overlay superior)
            # =============================================================================
            
            # Texto según vista
            if view_type == "PERFIL":
                if show_right:
                    info_text = f"CADERA DERECHA: {abs(angles['right_hip']):.0f}°"
                else:
                    info_text = f"CADERA IZQUIERDA: {abs(angles['left_hip']):.0f}°"
            else:  # FRONTAL
                info_text = f"CADERA IZQ: {abs(angles['left_hip']):.0f}° | DER: {abs(angles['right_hip']):.0f}°"
            
            # 🔧 Fallback si PIL falla
            result1 = self.add_text_with_pillow(frame, info_text, (10, 10), font_size=18, color=(255, 255, 255))
            if result1 is not None:
                frame = result1
            else:
                cv2.putText(frame, info_text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # 🧭 ORIENTACIÓN
            orientation_text = f"Vista: {view_type}"
            result2 = self.add_text_with_pillow(frame, orientation_text, (10, 40), font_size=16, color=(0, 255, 255))
            if result2 is not None:
                frame = result2
            else:
                cv2.putText(frame, orientation_text, (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    
        except Exception as e:
            # ⚠️ FIX: Si hay exception, retornar frame original (NO None)
            print(f"⚠️ Error en draw_joint_visualization: {e}")
            return frame
        
        # ✅ FIX CRÍTICO: SIEMPRE retornar frame al final
        return frame
    
    def add_text_with_pillow(self, frame, text, position, font_size=20, color=(255, 255, 255)):
        """🎨 Agregar texto con PIL (símbolos Unicode correctos)"""
        
        try:
            from PIL import Image, ImageDraw, ImageFont
            import numpy as np
            
            # ✅ FIX: Validar frame ANTES de procesar
            if frame is None:
                return None
            
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
            # Fallback: retornar frame original si PIL falla
            return frame
    
    def detect_pose(self, frame):
        """🦴 DETECTAR POSE - Método explícito para garantizar funcionamiento"""
        
        try:
            # Convertir BGR a RGB para MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Procesar pose
            results = self.pose.process(rgb_frame)
            
            if results.pose_landmarks:
                return results.pose_landmarks.landmark
            else:
                return None
                
        except Exception as e:
            print(f"⚠️ Error detectando pose en cadera: {e}")
            return None

    def reset_filters(self):
        """🔄 Resetear filtros temporales"""
        try:
            if hasattr(self, 'angle_filters'):
                self.angle_filters.clear()
                print("🔄 Filtros de cadera reseteados")
        except Exception as e:
            print(f"⚠️ Error reseteando filtros: {e}")
    
    # def _calculate_hip_angle_frontal(self, points, leg_side, orientation):
    #     """
    #     📐 MÉTODO CIENTÍFICO: Calcular ángulo de ABDUCCIÓN/ADUCCIÓN en vista FRONTAL
    #     🎯 Mide ángulo entre MUSLO y EJE VERTICAL (paciente de pie, pierna cuelga verticalmente)
    #     📏 Similar a goniómetro: eje vertical fijo, brazo móvil sigue muslo
    #     """
    #     pass  # Código comentado - ahora usamos calculate_abduction_angle() del test

    # def _calculate_hip_angle_sagital(self, points, leg_side):
    #     """
    #     📐 MÉTODO CIENTÍFICO: Calcular ángulo de FLEXIÓN de cadera en vista SAGITAL
    #     🎯 Mide ángulo entre MUSLO y EJE VERTICAL (igual que goniómetro)
    #     """
    #     pass  # Código comentado - ahora usamos calculate_flexion_extension_angle() del test

    # def _detect_abduction(self, hip, knee, hip_opposite, leg_side):
    #     """🎯 Detectar si el movimiento es abducción (pierna hacia el costado)"""
    #     pass  # Código comentado - ya no necesario con nuevo sistema