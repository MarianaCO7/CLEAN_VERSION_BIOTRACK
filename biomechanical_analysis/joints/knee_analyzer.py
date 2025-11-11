import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_analyzer import BaseJointAnalyzer
# 🔄 IMPORT ANTIGUO (COMENTADO - Reemplazado por detect_side_and_visibility() en línea ~76)
# from core.orientation_detector import AdaptiveOrientationDetector
import cv2
import numpy as np
import json

class KneeAnalyzer(BaseJointAnalyzer):
    """
    🦵 ANALIZADOR DE RODILLA
    📐 Análisis completo de flexión/extensión y valgo/varo
    🧭 Integrado con detección automática de orientación
    🎯 Usa TODAS las mejores prácticas del proyecto
    """
    
    def __init__(self):
        super().__init__("Knee")
        
        # 🆕 INICIALIZAR MEDIAPIPE EXPLÍCITAMENTE (como cadera exitosa)
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
            print("✅ MediaPipe inicializado correctamente para rodilla")
            
        except Exception as e:
            print(f"❌ Error inicializando MediaPipe rodilla: {e}")
            raise
        
        # 🔄 MÉTODO ANTIGUO DE ORIENTACIÓN (COMENTADO - Ya no se usa, reemplazado por detect_side_and_visibility())
        # Se mantiene comentado por si hay código legacy que lo necesite
        # self.orientation_detector = AdaptiveOrientationDetector()
        
        # 🦵 RANGOS NORMATIVOS DE RODILLA
        self.normal_ranges = {
            "knee_flexion": {"min": 0, "max": 135, "functional": 90},
            "knee_extension": {"min": 170, "max": 180, "functional": 180},
            "knee_separation": {"min": 5, "max": 25, "functional": 15}
        }
        
        # 🎯 SOPORTE MULTI-EJERCICIO
        self.current_exercise = "flexion"  # Default exercise
    
    def set_current_exercise(self, exercise_type: str):
        """
        Configura el ejercicio actual para el análisis
        🆕 Ahora lee camera_orientation desde exercises.json
        
        Args:
            exercise_type: Tipo de ejercicio ('flexion', 'extension')
        """
        valid_exercises = ['flexion', 'extension']
        if exercise_type in valid_exercises:
            self.current_exercise = exercise_type
            print(f"🎯 Ejercicio de rodilla configurado: {exercise_type}")
            
            # 🆕 CARGAR camera_orientation desde JSON (como hip/elbow)
            if not hasattr(self, 'exercise_configs'):
                # Cargar exercises.json una sola vez
                config_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'biomechanical_web_interface', 'config', 'exercises.json'
                )
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.exercise_configs = data['segments']['knee']['exercises']
                except Exception as e:
                    print(f"⚠️ Error cargando exercises.json: {e}")
                    self.exercise_configs = {}
            
            # 🆕 OBTENER camera_orientation del ejercicio actual
            if exercise_type in self.exercise_configs:
                exercise_data = self.exercise_configs[exercise_type]
                self.current_camera_orientation = exercise_data.get('camera_orientation', 'SAGITAL')
                print(f"📷 Camera orientation para {exercise_type}: {self.current_camera_orientation}")
            else:
                # Default: rodilla flexion/extension siempre es SAGITAL (perfil)
                self.current_camera_orientation = 'SAGITAL'
                print(f"⚠️ No se encontró config para {exercise_type}, usando 'SAGITAL' por defecto")
        else:
            print(f"⚠️ Ejercicio inválido: {exercise_type}. Usando flexion por defecto.")
            self.current_exercise = "flexion"
            self.current_camera_orientation = 'SAGITAL'
    
    def get_required_landmarks(self):
        """
        🦵 Landmarks para análisis completo de rodilla
        📊 Incluye caderas, rodillas y tobillos para análisis biomecánico completo
        """
        return [23, 24, 25, 26, 27, 28]  # Caderas, rodillas, tobillos
    
    def detect_side_and_visibility(self, landmarks):
        """
        🆕 DETECCIÓN DE ORIENTACIÓN MEJORADA - ADAPTADO DE TEST_KNEE_MOVEMENTS.PY
        
        Detecta qué lado del cuerpo está visible y hacia dónde mira la persona
        También determina si está de PERFIL o FRONTAL
        
        Returns:
            tuple: (tipo_vista, lado, confianza, orientacion, facing_direction)
                - tipo_vista: 'FRONTAL' o 'PERFIL'
                - lado: 'left', 'right' o None (si frontal) [ID de landmark]
                - confianza: float (0.0 a 1.0)
                - orientacion: str descripción legible
                - facing_direction: 'FRONTAL', 'IZQUIERDA', 'DERECHA' (hacia dónde mira)
        """
        # Obtener puntos clave (rodilla usa cadera y rodilla para visibilidad)
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
        right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value]
        left_knee = landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE.value]
        right_knee = landmarks[self.mp_pose.PoseLandmark.RIGHT_KNEE.value]
        nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
        
        # Calcular visibilidad de cada lado (incluye rodilla para mejor detección)
        left_visibility = (left_hip.visibility + left_knee.visibility) / 2
        right_visibility = (right_hip.visibility + right_knee.visibility) / 2
        
        # Calcular distancia entre hombros (en coordenadas normalizadas)
        shoulder_distance = abs(right_shoulder.x - left_shoulder.x)
        
        # Calcular distancia entre caderas
        hip_distance = abs(right_hip.x - left_hip.x)
        
        # Promedio de visibilidad y distancias
        avg_visibility = (left_visibility + right_visibility) / 2
        avg_distance = (shoulder_distance + hip_distance) / 2
        
        # Calcular facing_direction basado en la posición de la nariz
        nose_x = nose.x
        shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2
        nose_offset = nose_x - shoulder_center_x
        
        # 🎯 PRIMERO: Determinar si está de FRENTE o PERFIL
        if avg_distance > 0.12 and avg_visibility > 0.6 and left_visibility > 0.5 and right_visibility > 0.5:
            # Vista FRONTAL - Para análisis bilateral
            view_type = "FRONTAL"
            side = None
            confidence = avg_visibility
            orientation = "de frente (Análisis BILATERAL)"
            
            # ✅ Calcular facing_direction SOLO si frontal
            if abs(nose_offset) < 0.05:
                facing_direction = "FRONTAL"
            elif nose_offset < 0:
                facing_direction = "IZQUIERDA"
            else:
                facing_direction = "DERECHA"
        else:
            # Vista de PERFIL - Para análisis de flexión/extensión
            view_type = "SAGITAL"  # ✅ CORREGIDO: Usar "SAGITAL" (consistente con otros analyzers)
            
            # 🪞 ESPEJO MediaPipe: left_knee (landmark 25) = pierna DERECHA usuario
            #                      right_knee (landmark 26) = pierna IZQUIERDA usuario
            if left_visibility > right_visibility:
                # Landmark LEFT más visible → pierna DERECHA del usuario
                side = 'right'  # ✅ Corregido: devolver 'right' (lado usuario, no landmark)
                confidence = left_visibility
                orientation = "mirando izquierda" if nose_x < shoulder_center_x else "mirando derecha"
                # ✅ PERFIL: facing debe ser IZQUIERDA o DERECHA (nunca FRONTAL)
                facing_direction = "IZQUIERDA" if nose_offset < 0 else "DERECHA"
            else:
                # Landmark RIGHT más visible → pierna IZQUIERDA del usuario
                side = 'left'  # ✅ Corregido: devolver 'left' (lado usuario, no landmark)
                confidence = right_visibility
                orientation = "mirando derecha" if nose_x > shoulder_center_x else "mirando izquierda"
                # ✅ PERFIL: facing debe ser IZQUIERDA o DERECHA (nunca FRONTAL)
                facing_direction = "IZQUIERDA" if nose_offset < 0 else "DERECHA"
        
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
            - Ejercicio FRONTAL → requiere facing='FRONTAL'
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
                    print(f"⏱️ [KNEE] Timeout {force_accept_after_seconds}s alcanzado - ACEPTANDO orientación automáticamente")
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
                print(f"🧭 [KNEE validate_orientation_by_facing]")
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
            print(f"❌ Error validando orientación KNEE: {e}")
            return True
    
    def calculate_joint_angles(self, landmarks, frame_dimensions):
        """
        🦵 MÉTODO CIENTÍFICO: Cálculo de ángulos de rodilla con MÉTODO DE 3 PUNTOS
        📐 Ángulo interno: cadera-rodilla-tobillo (replica goniómetro clínico)
        🎯 Validable con ACSM/APTA - Norkin & White (2016)
        
        ⚠️ CRÍTICO: Rodilla mide FLEXIÓN interna, NO elevación vs gravedad
        """
        h, w = frame_dimensions
        
        try:
            # 🧭 DETECCIÓN DE ORIENTACIÓN (NUEVO MÉTODO - 5 valores)
            view_type, detected_side, confidence, orientation, facing_direction = self.detect_side_and_visibility(landmarks)
            
            # 🦵 ANÁLISIS PIERNA DERECHA
            right_result = self._analyze_single_leg(landmarks, w, h, 'RIGHT')
            
            # 🦵 ANÁLISIS PIERNA IZQUIERDA  
            left_result = self._analyze_single_leg(landmarks, w, h, 'LEFT')
            
            # 🎯 SELECCIONAR PIERNA PRINCIPAL (SAGITAL/PERFIL = una sola, FRONTAL = ambas)
            if view_type in ["SAGITAL", "PERFIL"]:  # ✅ Aceptar ambos nombres (compatibilidad)
                # En perfil/sagital, usar detected_side del método nuevo
                primary_leg = detected_side.upper() if detected_side else "RIGHT"
            else:
                primary_leg = "BOTH"
            
            # 📊 COMPATIBILIDAD: Crear orientation_info en formato antiguo (para no romper frontend)
            orientation_info = {
                'orientation': 'SAGITAL' if view_type == 'PERFIL' else 'FRONTAL',
                'confidence': confidence,
                'detected_side': detected_side,
                'view_type': view_type,
                'orientation_text': orientation,
                'landmark_set_used': 'NIVEL_1'  # Para compatibilidad
            }
            
            # 🪞 INTERCAMBIO ESPEJO MediaPipe (siguiendo patrón shoulder exitoso)
            # MediaPipe: left_knee (25) = pierna DERECHA usuario
            #            right_knee (26) = pierna IZQUIERDA usuario
            # Entonces intercambiamos antes de return para que coincida con lado real
            raw_right_corrected = left_result.get('raw_angle', 0)   # ✅ Landmark LEFT = pierna DERECHA
            raw_left_corrected = right_result.get('raw_angle', 0)   # ✅ Landmark RIGHT = pierna IZQUIERDA
            filtered_right_corrected = left_result.get('angle', 0)  # ✅ Filtrado para display
            filtered_left_corrected = right_result.get('angle', 0)  # ✅ Filtrado para display
            
            # 📊 ESTRUCTURA DE DATOS (patrón consistente)
            angles = {
                'right_knee': filtered_right_corrected,  # ✅ Intercambiado
                'left_knee': filtered_left_corrected,    # ✅ Intercambiado
                'raw_right': raw_right_corrected,        # ✅ Intercambiado para ROM tracking
                'raw_left': raw_left_corrected,          # ✅ Intercambiado para ROM tracking
                'right_movement_type': left_result.get('movement_type', 'FLEXION'),   # ✅ Intercambiado
                'left_movement_type': right_result.get('movement_type', 'FLEXION'),   # ✅ Intercambiado
                'positions': self._get_positions(landmarks, w, h),
                'orientation_info': orientation_info,
                'primary_leg': primary_leg,
                'right_leg_quality': left_result.get('quality', 0),   # ✅ Intercambiado
                'left_leg_quality': right_result.get('quality', 0),   # ✅ Intercambiado
                'view_type': view_type,  # ✅ Agregar para validación en handler
                'detected_side': detected_side  # ✅ Agregar para ROM tracking
            }
            
        except Exception as e:
            print(f"❌ Error en cálculo de rodilla: {e}")
            import traceback
            traceback.print_exc()
            angles = {
                'right_knee': 0, 'left_knee': 0,
                'raw_right': 0, 'raw_left': 0,
                'right_movement_type': 'ERROR', 'left_movement_type': 'ERROR',
                'positions': {}, 'orientation_info': {'orientation': 'ERROR', 'confidence': 0.0},
                'primary_leg': 'BOTH', 'right_leg_quality': 0, 'left_leg_quality': 0,
                'view_type': 'ERROR', 'detected_side': None
            }
        
        return angles
    
    def _analyze_single_leg(self, landmarks, w, h, leg_side):
        """
        🦵 ANÁLISIS CIENTÍFICO DE UNA SOLA PIERNA (MÉTODO 3 PUNTOS)
        📐 Calcula ángulo INTERNO: cadera-rodilla-tobillo
        🎯 Replica EXACTAMENTE el goniómetro manual clínico
        🔬 Validable con ACSM/APTA standards
        """
        
        # Seleccionar landmarks según lado
        if leg_side == 'RIGHT':
            hip_idx, knee_idx, ankle_idx = 24, 26, 28  # Derecha
        else:
            hip_idx, knee_idx, ankle_idx = 23, 25, 27  # Izquierda
        
        # Verificar visibilidad de los 3 puntos necesarios.
        # Antes: retornábamos ERROR si cualquiera < 0.3 y eso dejaba ángulos siempre en 0
        # Ahora: si los puntos están casi ausentes (visibility < 0.05) no es posible calcular.
        # Pero si existen aunque con baja confianza, calculamos el ángulo RAW y devolvemos
        # una calidad baja en lugar de 0 absoluto. Esto mejora la disponibilidad de ángulos
        # para la overlay del frontend mientras la detección mejora.
        vis_hip = landmarks[hip_idx].visibility
        vis_knee = landmarks[knee_idx].visibility
        vis_ankle = landmarks[ankle_idx].visibility

        # Si alguno está esencialmente ausente, no podemos calcular
        if (vis_hip < 0.05 or vis_knee < 0.05 or vis_ankle < 0.05):
            return {'angle': 0, 'movement_type': 'ERROR', 'quality': 0}
        
        # Puntos de la pierna
        hip = [landmarks[hip_idx].x * w, landmarks[hip_idx].y * h]
        knee = [landmarks[knee_idx].x * w, landmarks[knee_idx].y * h]
        ankle = [landmarks[ankle_idx].x * w, landmarks[ankle_idx].y * h]
        
        # 🎯 CÁLCULO CIENTÍFICO: Ángulo interno de 3 puntos (como goniómetro)
        raw_angle = self.calculate_angle_biomechanical(hip, knee, ankle)
        
        # 🔄 INVERTIR ÁNGULO: Goniómetro mide flexión desde 0° (recto) hasta 135° (flexionado)
        # calculate_angle_biomechanical() da ángulo interno: 180° (recto) → 45° (flexionado)
        # Necesitamos: 0° (recto) → 135° (flexionado)
        angle = 180 - raw_angle
        
        # 🔍 DEBUG: Verificar cálculo (COMENTADO para reducir logs Railway)
        # print(f"🧮 {leg_side} KNEE: Raw={raw_angle:.1f}°, Invertido={angle:.1f}° | Hip:{hip[1]:.0f}, Knee:{knee[1]:.0f}, Ankle:{ankle[1]:.0f}")
        
        # � APLICAR FILTRO TEMPORAL (mejora de estabilidad)
        filter_key = f'{leg_side.lower()}_knee'
        filtered_angle = self.apply_temporal_filter(angle, filter_key)
        
        # Calidad de detección (3 factores) - Threshold 0.3 para garantizar calidad
        quality_score = 0
        if landmarks[hip_idx].visibility > 0.3: quality_score += 1
        if landmarks[knee_idx].visibility > 0.3: quality_score += 1
        if landmarks[ankle_idx].visibility > 0.3: quality_score += 1
        
        # 🏥 CLASIFICACIÓN CLÍNICA (Norkin & White 2016 + imagen proporcionada)
        # Sistema: 0° = recto (extensión completa), 135-140° = flexión óptima
        if filtered_angle < 90:
            movement_type = 'FLEXION PROFUNDA'  # <90° = Flexión profunda (limitada/severa)
        elif filtered_angle < 110:
            movement_type = 'FUNCIONAL MINIMO'  # 90-110° = Funcional mínimo para AVD
        elif filtered_angle < 135:
            movement_type = 'FLEXION'  # 110-135° = Rango funcional
        elif filtered_angle < 140:
            movement_type = 'NORMAL/OPTIMO'  # 135-140° = Rango óptimo
        elif filtered_angle < 150:
            movement_type = 'HIPERMOVIL/EXCESIVO'  # >140° = Hipermóvil (puede indicar laxitud)
        else:
            movement_type = 'EXTENSION'  # >150° = Extensión (cerca de recto)
        
        return {
            'angle': filtered_angle,
            'raw_angle': angle,
            'movement_type': movement_type,
            'quality': quality_score
        }
    
    def _select_primary_leg(self, landmarks, right_result, left_result):
        """
        🎯 SELECCIONAR PIERNA PRINCIPAL en vista SAGITAL
        📐 Prioridad: 1) Z-depth (más cerca), 2) Calidad, 3) Ángulo válido, 4) Visibilidad
        """
        right_quality = right_result.get('quality', 0)
        left_quality = left_result.get('quality', 0)
        right_angle = right_result.get('angle', 0)
        left_angle = left_result.get('angle', 0)
        
        # 🎯 PRIORIDAD 1: Z-DEPTH (pierna más cercana a la cámara)
        # MediaPipe usa coordenada Z donde menor valor = más cerca
        right_knee_z = landmarks[26].z if hasattr(landmarks[26], 'z') else 0
        left_knee_z = landmarks[25].z if hasattr(landmarks[25], 'z') else 0
        
        # Si hay diferencia significativa en profundidad (>0.05), priorizar la más cercana
        z_diff = abs(right_knee_z - left_knee_z)
        if z_diff > 0.05:
            if right_knee_z < left_knee_z:  # Derecha más cerca
                # 🔇 CACHE: Solo imprimir cuando cambia la pierna principal
                if not hasattr(self, '_last_primary_leg') or self._last_primary_leg != 'RIGHT':
                    print(f"🎯 PRIMARY_LEG: RIGHT (Z-depth: {right_knee_z:.3f} < {left_knee_z:.3f})")
                    self._last_primary_leg = 'RIGHT'
                return 'RIGHT'
            else:  # Izquierda más cerca
                # 🔇 CACHE: Solo imprimir cuando cambia la pierna principal
                if not hasattr(self, '_last_primary_leg') or self._last_primary_leg != 'LEFT':
                    print(f"🎯 PRIMARY_LEG: LEFT (Z-depth: {left_knee_z:.3f} < {right_knee_z:.3f})")
                    self._last_primary_leg = 'LEFT'
                return 'LEFT'
        
        # 2. Priorizar por calidad de detección (3 factores)
        if right_quality > left_quality:
            return 'RIGHT'
        elif left_quality > right_quality:
            return 'LEFT'
        
        # 3. Si calidad igual, priorizar por ángulo válido (no 0)
        if right_angle > 5 and left_angle <= 5:
            return 'RIGHT'
        elif left_angle > 5 and right_angle <= 5:
            return 'LEFT'
        
        # 4. Si ambos válidos o inválidos, verificar visibilidad de rodilla
        right_knee_vis = landmarks[26].visibility  # Rodilla derecha
        left_knee_vis = landmarks[25].visibility   # Rodilla izquierda
        
        if right_knee_vis > left_knee_vis:
            return 'RIGHT'
        elif left_knee_vis > right_knee_vis:
            return 'LEFT'
        
        # 4. Default: derecha
        return 'RIGHT'
    
    def _get_positions(self, landmarks, w, h):
        """📍 Obtener posiciones de landmarks para visualización"""
        try:
            return {
                'hip_r': [landmarks[24].x * w, landmarks[24].y * h],
                'knee_r': [landmarks[26].x * w, landmarks[26].y * h],
                'ankle_r': [landmarks[28].x * w, landmarks[28].y * h],
                'hip_l': [landmarks[23].x * w, landmarks[23].y * h],
                'knee_l': [landmarks[25].x * w, landmarks[25].y * h],
                'ankle_l': [landmarks[27].x * w, landmarks[27].y * h]
            }
        except:
            return {}
    
    def draw_joint_visualization(self, frame, landmarks, angles):
        """
        🦵 VISUALIZACIÓN DE RODILLAS - ADAPTADA DE TEST_KNEE_MOVEMENTS.PY
        🎨 Puntos GRANDES con colores específicos (igual que test)
        📐 Líneas VERDES para muslo/pantorrilla (replica test)
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
            
            # 🦵 VISUALIZACIÓN SEGÚN VISTA
            
            # ✅ VISTA PERFIL/SAGITAL - Solo lado activo (igual test líneas 246-261)
            if view_type in ['PERFIL', 'SAGITAL'] or primary_leg != 'BOTH':  # ✅ Aceptar ambos nombres
                
                # Determinar qué lado dibujar
                if primary_leg == 'RIGHT':
                    if all(pos.get(key) for key in ['hip_r', 'knee_r', 'ankle_r']):
                        hip_2d = tuple(map(int, pos['hip_r']))
                        knee_2d = tuple(map(int, pos['knee_r']))
                        ankle_2d = tuple(map(int, pos['ankle_r']))
                        angle = angles.get('right_knee', 0)
                        movement_type = angles.get('right_movement_type', 'FLEXION')
                        
                        # 🎨 PUNTOS GRANDES (test líneas 246-248)
                        cv2.circle(frame, hip_2d, 8, (255, 255, 0), -1)      # Cyan - Cadera
                        cv2.circle(frame, knee_2d, 10, (255, 0, 255), -1)    # Magenta - Rodilla (vértice)
                        cv2.circle(frame, ankle_2d, 8, (0, 255, 255), -1)    # Amarillo - Tobillo
                        
                        # 🎨 LÍNEAS VERDES (test líneas 250-251)
                        cv2.line(frame, hip_2d, knee_2d, (0, 255, 0), 4)     # Verde - Muslo
                        cv2.line(frame, knee_2d, ankle_2d, (0, 255, 0), 3)   # Verde - Pantorrilla
                        
                        # 📐 ÁNGULO GRANDE (test línea 253-256)
                        cv2.putText(frame, f"{angle:.1f}", 
                                   (knee_2d[0] + 20, knee_2d[1] - 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 4)
                        
                        # 📊 TIPO MOVIMIENTO (test línea 258-261)
                        movement_color = (0, 255, 0) if angle > 110 else (0, 165, 255) if angle > 90 else (0, 0, 255)
                        cv2.putText(frame, movement_type, 
                                   (knee_2d[0] + 20, knee_2d[1] + 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, movement_color, 2)
                
                elif primary_leg == 'LEFT':
                    if all(pos.get(key) for key in ['hip_l', 'knee_l', 'ankle_l']):
                        hip_2d = tuple(map(int, pos['hip_l']))
                        knee_2d = tuple(map(int, pos['knee_l']))
                        ankle_2d = tuple(map(int, pos['ankle_l']))
                        angle = angles.get('left_knee', 0)
                        movement_type = angles.get('left_movement_type', 'FLEXION')
                        
                        # 🎨 PUNTOS GRANDES (idéntico a RIGHT)
                        cv2.circle(frame, hip_2d, 8, (255, 255, 0), -1)      # Cyan - Cadera
                        cv2.circle(frame, knee_2d, 10, (255, 0, 255), -1)    # Magenta - Rodilla
                        cv2.circle(frame, ankle_2d, 8, (0, 255, 255), -1)    # Amarillo - Tobillo
                        
                        # 🎨 LÍNEAS VERDES (idéntico a RIGHT)
                        cv2.line(frame, hip_2d, knee_2d, (0, 255, 0), 4)     # Verde - Muslo
                        cv2.line(frame, knee_2d, ankle_2d, (0, 255, 0), 3)   # Verde - Pantorrilla
                        
                        # 📐 ÁNGULO GRANDE
                        cv2.putText(frame, f"{angle:.1f}", 
                                   (knee_2d[0] - 80, knee_2d[1] - 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 4)
                        
                        # 📊 TIPO MOVIMIENTO
                        movement_color = (0, 255, 0) if angle > 110 else (0, 165, 255) if angle > 90 else (0, 0, 255)
                        cv2.putText(frame, movement_type, 
                                   (knee_2d[0] - 150, knee_2d[1] + 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, movement_color, 2)
            
            # ✅ VISTA FRONTAL - Ambos lados (test líneas 283-337)
            elif view_type == 'FRONTAL' or primary_leg == 'BOTH':
                
                # 🦵 PIERNA IZQUIERDA
                if all(pos.get(key) for key in ['hip_l', 'knee_l', 'ankle_l']):
                    left_hip_2d = tuple(map(int, pos['hip_l']))
                    left_knee_2d = tuple(map(int, pos['knee_l']))
                    left_ankle_2d = tuple(map(int, pos['ankle_l']))
                    left_angle = angles.get('left_knee', 0)
                    left_state = angles.get('left_movement_type', 'FLEXION')
                    
                    # 🎨 PUNTOS GRANDES (test líneas 318-320)
                    cv2.circle(frame, left_hip_2d, 8, (255, 255, 0), -1)      # Cyan - Cadera
                    cv2.circle(frame, left_knee_2d, 10, (255, 0, 255), -1)    # Magenta - Rodilla
                    cv2.circle(frame, left_ankle_2d, 8, (0, 255, 255), -1)    # Amarillo - Tobillo
                    
                    # 🎨 LÍNEAS VERDES (test líneas 327-328)
                    cv2.line(frame, left_hip_2d, left_knee_2d, (0, 255, 0), 4)     # Verde - Muslo
                    cv2.line(frame, left_knee_2d, left_ankle_2d, (0, 255, 0), 3)   # Verde - Pantorrilla
                    
                    # 📐 ÁNGULO (test líneas 330-333)
                    cv2.putText(frame, f"{left_angle:.1f}", 
                               (left_knee_2d[0] - 80, left_knee_2d[1] - 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 255, 255), 3)
                    
                    # 📊 ESTADO (test líneas 342-345)
                    left_color = (0, 255, 0) if left_angle > 110 else (0, 165, 255) if left_angle > 90 else (0, 0, 255)
                    cv2.putText(frame, left_state, 
                               (left_knee_2d[0] - 70, left_knee_2d[1] + 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, left_color, 2)
                
                # 🦵 PIERNA DERECHA
                if all(pos.get(key) for key in ['hip_r', 'knee_r', 'ankle_r']):
                    right_hip_2d = tuple(map(int, pos['hip_r']))
                    right_knee_2d = tuple(map(int, pos['knee_r']))
                    right_ankle_2d = tuple(map(int, pos['ankle_r']))
                    right_angle = angles.get('right_knee', 0)
                    right_state = angles.get('right_movement_type', 'FLEXION')
                    
                    # 🎨 PUNTOS GRANDES (test líneas 323-325)
                    cv2.circle(frame, right_hip_2d, 8, (255, 255, 0), -1)     # Cyan - Cadera
                    cv2.circle(frame, right_knee_2d, 10, (255, 0, 255), -1)   # Magenta - Rodilla
                    cv2.circle(frame, right_ankle_2d, 8, (0, 255, 255), -1)   # Amarillo - Tobillo
                    
                    # 🎨 LÍNEAS VERDES (test líneas 330-331)
                    cv2.line(frame, right_hip_2d, right_knee_2d, (0, 255, 0), 4)   # Verde - Muslo
                    cv2.line(frame, right_knee_2d, right_ankle_2d, (0, 255, 0), 3) # Verde - Pantorrilla
                    
                    # 📐 ÁNGULO (test líneas 335-338)
                    cv2.putText(frame, f"{right_angle:.1f}", 
                               (right_knee_2d[0] + 30, right_knee_2d[1] - 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 255, 255), 3)
                    
                    # 📊 ESTADO (test líneas 347-350)
                    right_color = (0, 255, 0) if right_angle > 110 else (0, 165, 255) if right_angle > 90 else (0, 0, 255)
                    cv2.putText(frame, right_state, 
                               (right_knee_2d[0] + 20, right_knee_2d[1] + 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, right_color, 2)
            
            # 📊 INFORMACIÓN SUPERIOR (simple, sin PIL)
            cv2.putText(frame, f"Vista: {view_type} | Lado: {primary_leg}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
        except Exception as e:
            cv2.putText(frame, f"ERROR VISUALIZACION: {str(e)[:40]}", (10, 130), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        return frame
    
    # 🔄 MÉTODO ANTIGUO - COMENTADO (Reemplazado por visualización test línea ~335)
    # def _draw_orientation_info(self, frame, orientation_info):
    #     """
    #     🧭 INFORMACIÓN DE ORIENTACIÓN
    #     📍 Misma implementación exitosa de shoulder/elbow
    #     """
    #     if not orientation_info or orientation_info.get('orientation') == 'ERROR':
    #         return
    #     
    #     h, w, _ = frame.shape
    #     
    #     # 📍 ÁREA SUPERIOR DERECHA
    #     info_x = w - 300
    #     info_y = 30
    #     
    #     # 🧭 DATOS PRINCIPALES
    #     orientation = orientation_info.get('orientation', 'UNKNOWN')
    #     confidence = orientation_info.get('confidence', 0.0)
    #     level = orientation_info.get('landmark_set_used', 'UNKNOWN')
    #     
    #     # 📊 MOSTRAR INFO
    #     #cv2.putText(frame, f"Plano: {orientation}", 
    #     #           (info_x, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    #     
    #     #cv2.putText(frame, f"Confianza: {confidence:.0%}", 
    #     #           (info_x, info_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    #     
    #     #cv2.putText(frame, f"Nivel: {level}", 
    #     #           (info_x, info_y + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    #     
    #     # 💡 RECOMENDACIÓN
    #     recommendations = orientation_info.get('recommendations', [])
    #     if recommendations:
    #         main_rec = recommendations[0]
    #         if len(main_rec) > 40:
    #             main_rec = main_rec[:37] + "..."
    #         #cv2.putText(frame, main_rec, 
    #         #           (info_x, info_y + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 0), 1)
    #     
    #     # 🎯 INDICADOR DE CALIDAD
    #     color = (0, 255, 0) if confidence > 0.8 else (0, 255, 255) if confidence > 0.6 else (0, 0, 255)
    #     cv2.circle(frame, (info_x - 15, info_y + 5), 8, color, -1)
    
    def check_required_points_visible(self, landmarks):
        """Verificar visibilidad de puntos para rodillas - MAS TOLERANTE"""
        
        if not landmarks or len(landmarks) < 29:
            return False
        
        # 🎯 UMBRALES MUY PERMISIVOS PARA DEBUGGING
        visibility_threshold = 0.3  # MUY permisivo
        min_legs_required = 1       # Solo una pierna necesaria
        
        # 📊 EVALUAR PIERNAS CON LOGS DETALLADOS
        legs_valid = 0
        
        # Pierna izquierda [23, 25, 27] (cadera, rodilla, tobillo)
        left_visibilities = [landmarks[idx].visibility if idx < len(landmarks) else 0 
                            for idx in [23, 25, 27]]
        left_points = sum(1 for v in left_visibilities if v > visibility_threshold)
        
        # 🔇 CACHE: Solo imprimir cuando cambia el tipo
        cache_key_left = f"left_{left_points}"
        if not hasattr(self, '_last_check_left') or self._last_check_left != cache_key_left:
            print(f"🔍 PIERNA IZQ visibilities: {[f'{v:.2f}' for v in left_visibilities]}")
            self._last_check_left = cache_key_left
        
        if left_points >= 2:  # Al menos 2 de 3 puntos
            legs_valid += 1
            if not hasattr(self, '_last_left_valid') or self._last_left_valid != True:
                print(f"✅ PIERNA IZQUIERDA: {left_points}/3 puntos válidos")
                self._last_left_valid = True
        else:
            self._last_left_valid = False
        
        # Pierna derecha [24, 26, 28]
        right_visibilities = [landmarks[idx].visibility if idx < len(landmarks) else 0 
                             for idx in [24, 26, 28]]
        right_points = sum(1 for v in right_visibilities if v > visibility_threshold)
        
        # 🔇 CACHE: Solo imprimir cuando cambia el tipo
        cache_key_right = f"right_{right_points}"
        if not hasattr(self, '_last_check_right') or self._last_check_right != cache_key_right:
            print(f"🔍 PIERNA DER visibilities: {[f'{v:.2f}' for v in right_visibilities]}")
            self._last_check_right = cache_key_right
        
        if right_points >= 2:  # Al menos 2 de 3 puntos
            legs_valid += 1
            if not hasattr(self, '_last_right_valid') or self._last_right_valid != True:
                print(f"✅ PIERNA DERECHA: {right_points}/3 puntos válidos")
                self._last_right_valid = True
        else:
            self._last_right_valid = False
        
        is_valid = legs_valid >= min_legs_required
        
        # 🔇 CACHE: Solo imprimir cuando cambia el resultado
        if not hasattr(self, '_last_check_result') or self._last_check_result != is_valid:
            print(f"🎯 CHECK RODILLA: {legs_valid} piernas válidas → {'✅ VÁLIDO' if is_valid else '❌ INVÁLIDO'}")
            self._last_check_result = is_valid
        
        return is_valid
    
    def detect_pose(self, frame):
        """DETECTAR POSE - Metodo explicito para rodilla"""
        
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
            print(f"⚠️ Error en detect_pose rodilla: {e}")
            return None
    
    # 🔄 MÉTODO ANTIGUO - COMENTADO (Ya no se usa con visualización test)
    # def add_text_with_pillow(self, frame, text, position, font_size=20, color=(255, 255, 255)):
    #     """🎨 Agregar texto con PIL (símbolos Unicode correctos)"""
    #     
    #     try:
    #         from PIL import Image, ImageDraw, ImageFont
    #         import numpy as np
    #         
    #         # Convertir a PIL
    #         pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    #         draw = ImageDraw.Draw(pil_image)
    #         
    #         # Fuente
    #         try:
    #             font = ImageFont.truetype("arial.ttf", font_size)
    #         except:
    #             font = ImageFont.load_default()
    #         
    #         # Dibujar texto
    #         draw.text(position, text, font=font, fill=color)
    #         
    #         # Convertir de vuelta
    #         return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    #         
    #     except Exception as e:
    #         # Fallback a OpenCV si PIL falla
    #         #cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 
    #         #           font_size/30, color, 2)
    #         return frame
    
    def reset_filters(self):
        """Resetear filtros temporales"""
        try:
            if hasattr(self, 'angle_filters'):
                self.angle_filters.clear()
                print("🔄 Filtros de rodilla reseteados")
        except Exception as e:
            print(f"⚠️ Error reseteando filtros: {e}")