import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_analyzer import BaseJointAnalyzer
from core.orientation_detector import AdaptiveOrientationDetector  # 🆕 AÑADIR
import cv2
import numpy as np
import math

class ElbowAnalyzer(BaseJointAnalyzer):
    """
    🎯 ANALIZADOR DE CODO
    📋 CONSERVA tu lógica EXACTA + detección de orientación
    ✅ MISMO funcionamiento + información adicional
    """
    
    def __init__(self):
        super().__init__("Elbow")
        self.orientation_detector = AdaptiveOrientationDetector()
        # 🆕 ESTABILIDAD DE ORIENTACIÓN
        self.orientation_history = []
        self.current_stable_orientation = "FRONTAL"  # ✅ Empezar con FRONTAL
        # 🆕 EVITAR CAMBIOS MUY FRECUENTES
        self.orientation_change_cooldown = 0
        # 🎯 SOPORTE MULTI-EJERCICIO
        self.current_exercise = "flexion"  # Default exercise
        # 🆕 ORIENTACIÓN AUTORITARIA DEL JSON (override del detector)
        self.orientation_override = None  # Si está set, ignora detector
        # 🆕 CAMERA ORIENTATION desde exercises.json (FIX 4 - igual que shoulder)
        self.current_camera_orientation = 'sagital'  # Default
        self.exercise_configs = None  # Se cargará en set_current_exercise()
    
    def set_orientation_override(self, orientation):
        """
        🎯 SETEA ORIENTACIÓN AUTORITARIA del JSON
        Esta orientación prevalece sobre el detector automático
        
        Args:
            orientation: 'SAGITAL', 'FRONTAL', 'TRANSVERSAL' o None (usar detector)
        """
        self.orientation_override = orientation
        if orientation:
            print(f"📋 Orientación JSON override: {orientation} (ignora detector)")
        else:
            print(f"🤖 Usando detector automático de orientación")
    
    def set_current_exercise(self, exercise_type: str):
        """
        Configura el ejercicio actual para el análisis
        🆕 FIX 4: Ahora lee camera_orientation desde exercises.json
        
        Args:
            exercise_type: Tipo de ejercicio ('flexion', 'extension', 'overhead_extension')
        """
        valid_exercises = ['flexion', 'extension', 'overhead_extension']
        if exercise_type in valid_exercises:
            self.current_exercise = exercise_type
            print(f"🎯 Ejercicio de codo configurado: {exercise_type}")
            
            # 🆕 CARGAR camera_orientation desde exercises.json
            if self.exercise_configs is None:
                import json
                import os
                config_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'biomechanical_web_interface', 'config', 'exercises.json'
                )
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.exercise_configs = data['segments']['elbow']['exercises']
                except Exception as e:
                    print(f"⚠️ Error cargando exercises.json: {e}")
                    self.exercise_configs = {}
            
            # 🆕 OBTENER camera_orientation del ejercicio actual
            if exercise_type in self.exercise_configs:
                exercise_data = self.exercise_configs[exercise_type]
                self.current_camera_orientation = exercise_data.get('camera_orientation', 'sagital')
                print(f"📷 Camera orientation para {exercise_type}: {self.current_camera_orientation}")
            else:
                self.current_camera_orientation = 'sagital'  # Default
                print(f"⚠️ No se encontró config para {exercise_type}, usando 'sagital' por defecto")
        else:
            print(f"⚠️ Ejercicio inválido: {exercise_type}. Usando flexion por defecto.")
            self.current_exercise = "flexion"
            self.current_camera_orientation = 'sagital'
    
    def get_required_landmarks(self):
        """
        Landmarks para análisis de codo
        MIGRADO EXACTO desde test_elbow_upper_body.py
        """
        return [11, 12, 13, 14, 15, 16]  # Hombros, codos, muñecas
    
    def detect_side_and_visibility(self, landmarks):
        """
        🆕 DETECCIÓN DE ORIENTACIÓN MEJORADA - Con facing_direction
        
        Detecta qué lado del cuerpo está visible y hacia dónde mira la persona
        También determina si está de PERFIL o FRONTAL
        
        Returns:
            tuple: (tipo_vista, lado, confianza, orientacion, facing_direction)
                - tipo_vista: 'FRONTAL' o 'SAGITAL'
                - lado: 'left', 'right' o None (si frontal) [ID de landmark]
                - confianza: float (0.0 a 1.0)
                - orientacion: str descripción legible
                - facing_direction: 'left', 'right', 'front', 'unknown' [dirección real de mirada]
        
        NOTA: Para análisis de CODO, se recomienda vista SAGITAL (perfil)
        """
        # 🎯 IMPORT DE MEDIAPIPE (ya debe estar disponible)
        try:
            import mediapipe as mp
            mp_pose = mp.solutions.pose
        except ImportError:
            print("⚠️ MediaPipe no disponible")
            return 'SAGITAL', 'right', 0.5, 'detectando...', 'unknown'  # 🆕 Retorna 5 valores
        
        # Obtener puntos clave
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        nose = landmarks[mp_pose.PoseLandmark.NOSE.value]
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
        
        # Calcular visibilidad de cada lado
        left_visibility = left_shoulder.visibility
        right_visibility = right_shoulder.visibility
        
        # Calcular distancia entre hombros (en coordenadas normalizadas)
        shoulder_distance = abs(right_shoulder.x - left_shoulder.x)
        
        # Calcular distancia entre caderas
        hip_distance = abs(right_hip.x - left_hip.x)
        
        # Determinar si está de FRENTE o PERFIL
        # Si ambos hombros son muy visibles Y la distancia entre ellos es grande = FRONTAL
        # 🆕 UMBRALES MÁS ESTRICTOS (igual que shoulder): distancia > 0.15, visibilidad > 0.6
        # Esto evita detectar FRONTAL cuando está de perfil con ambos hombros visibles
        
        avg_shoulder_visibility = (left_visibility + right_visibility) / 2
        
        # � DEBUG COMENTADO: Causa lag (30 prints/segundo)
        # print(f"🔍 ELBOW DETECTION: shoulder_distance={shoulder_distance:.3f} (>0.15?), avg_vis={avg_shoulder_visibility:.3f}, L={left_visibility:.3f}, R={right_visibility:.3f}")
        
        if shoulder_distance > 0.15 and avg_shoulder_visibility > 0.6 and left_visibility > 0.6 and right_visibility > 0.6:
            # Vista FRONTAL - No recomendada para codo
            view_type = "FRONTAL"
            side = None  # No aplica en vista frontal
            confidence = avg_shoulder_visibility
            orientation = "de frente"
            facing_direction = 'front'  # 🆕 En vista frontal, siempre es 'front'
        else:
            # Vista SAGITAL (de PERFIL) - RECOMENDADA para codo
            # 🆕 FIX 7: Cambio "PERFIL" → "SAGITAL" para consistencia biomecánica
            view_type = "SAGITAL"
            
            # Determinar orientación basado en la posición de la nariz respecto a los hombros
            nose_x = nose.x
            left_shoulder_x = left_shoulder.x
            right_shoulder_x = right_shoulder.x
            
            shoulder_center_x = (left_shoulder_x + right_shoulder_x) / 2
            
            # 🆕 CALCULAR facing_direction basado en posición de la nariz
            # Threshold: 0.05 (5% del ancho del frame normalizado)
            if nose_x < shoulder_center_x - 0.05:
                facing_direction = 'left'  # Nariz a la izquierda = mirando hacia la izquierda
            elif nose_x > shoulder_center_x + 0.05:
                facing_direction = 'right'  # Nariz a la derecha = mirando hacia la derecha
            else:
                facing_direction = 'unknown'  # En zona ambigua
            
            # Calcular qué brazo está más de perfil (más visible y más alejado de la nariz)
            # 🪞 MediaPipe: left_shoulder (landmark 11) = brazo derecho usuario (espejo)
            #              right_shoulder (landmark 12) = brazo izquierdo usuario (espejo)
            if left_visibility > right_visibility:
                # Landmark LEFT (11) más visible = brazo derecho del usuario
                side = 'left'  # Usamos 'left' como identificador de landmark, no de brazo real
                confidence = left_visibility
                orientation = "mirando izquierda" if nose_x < shoulder_center_x else "mirando derecha"
            else:
                # Landmark RIGHT (12) más visible = brazo izquierdo del usuario
                side = 'right'  # Usamos 'right' como identificador de landmark, no de brazo real
                confidence = right_visibility
                orientation = "mirando derecha" if nose_x > shoulder_center_x else "mirando izquierda"
        
        # 🆕 RETORNAR 5 VALORES (incluye facing_direction para compatibilidad con handler)
        return view_type, side, confidence, orientation, facing_direction
    
    def validate_orientation_by_facing(self, landmarks):
        """
        🎯 VALIDACIÓN MODERNA: Usa facing_direction (mirada) NO geometría de hombros
        
        Compara la orientación REQUERIDA (camera_orientation del ejercicio)
        con la DETECTADA (facing_direction basado en posición de nariz)
        
        Returns:
            bool: True si orientación correcta, False si incorrecta
            
        Lógica:
            - Ejercicio FRONTAL (abducción) → requiere facing='front'
            - Ejercicio SAGITAL (flexión/extensión) → requiere facing='left' o 'right'
        """
        try:
            # 🔍 DETECTAR orientación actual
            view_type, side, confidence, orientation, facing_direction = self.detect_side_and_visibility(landmarks)
            
            # 🎯 NORMALIZAR valores para comparación
            required_orientation = self.current_camera_orientation.lower()  # 'frontal' o 'sagital'
            detected_facing = facing_direction.lower()  # 'front', 'left', 'right', 'unknown'
            
            # 🔇 CACHE: Solo imprimir si cambia el estado (evitar spam que causa lag)
            cache_key = f"{detected_facing}_{required_orientation}"
            if not hasattr(self, '_last_validation_log') or self._last_validation_log != cache_key:
                print(f"🧭 [ELBOW validate_orientation_by_facing]")
                print(f"   Requerida: {required_orientation}")
                print(f"   Detectada: {detected_facing} (view_type={view_type})")
                self._last_validation_log = cache_key
            
            # 🎯 VALIDACIÓN SEGÚN TIPO DE EJERCICIO
            if required_orientation == 'frontal':
                # ✅ Ejercicio FRONTAL: necesita mirar de frente
                is_valid = (detected_facing == 'front')
                return is_valid
                
            elif required_orientation == 'sagital':
                # ✅ Ejercicio SAGITAL: necesita mirar left o right (perfil)
                is_valid = (detected_facing in ['left', 'right'])
                return is_valid
                
            else:
                # ⚠️ Orientación desconocida - aceptar por defecto
                return True
                
        except Exception as e:
            print(f"❌ Error validando orientación ELBOW: {e}")
            return False  # 🚨 Fallar seguro en caso de error
    
    def calculate_joint_angles(self, landmarks, frame_shape):
        """
        ✅ CÁLCULO SIMPLIFICADO - SOLO método correcto de test_elbow_flexion.py
        🎯 USA detect_side_and_visibility() para determinar qué calcular
        """
        h, w = frame_shape[:2]
        
        try:
            # 🧭 DETECCIÓN DE ORIENTACIÓN (EXACTA de test) - AHORA CON 5 VALORES
            view_type, side, confidence, orientation, facing_direction = self.detect_side_and_visibility(landmarks)
            
            orientation_info = {
                'orientation': 'SAGITAL' if view_type == 'SAGITAL' else 'FRONTAL',  # FIX 7: SAGITAL no PERFIL
                'confidence': confidence
            }
            
            # ✅ USAR SIEMPRE MÉTODO CORRECTO: _calculate_bilateral_angles
            angles = self._calculate_bilateral_angles(
                landmarks, w, h, orientation_info
            )
            
            return angles
                
        except Exception as e:
            print(f"❌ Error en cálculo de codo: {e}")
            return self._get_default_result()
    
    def _calculate_bilateral_angles(self, landmarks, w, h, orientation_info):
        """
        🆕 MÉTODO CORRECTO - ADAPTADO DE test_elbow_flexion.py
        
        USA: calculate_angle_biomechanical() de 3 puntos (hombro-codo-muñeca)
        Sistema: 0° = extensión completa, 150° = flexión máxima
        """
        
        # =============================================================================
        # LADO DERECHO - EXACTO DE test_elbow_flexion.py
        # =============================================================================
        shoulder_r = landmarks[12]
        elbow_r = landmarks[14]
        wrist_r = landmarks[16]
        
        # Convertir a coordenadas pixel
        shoulder_r_pos = [shoulder_r.x * w, shoulder_r.y * h]
        elbow_r_pos = [elbow_r.x * w, elbow_r.y * h]
        wrist_r_pos = [wrist_r.x * w, wrist_r.y * h]
        
        # 🆕 CALCULAR ÁNGULO GEOMÉTRICO (3 puntos)
        geometric_angle_r = self.calculate_angle_biomechanical(
            shoulder_r_pos, elbow_r_pos, wrist_r_pos
        )
        
        # 🔄 CONVERSIÓN A ÁNGULO CLÍNICO
        # Geométrico: 180° = extensión, 35° = flexión
        # Clínico: 0° = extensión, 145° = flexión
        angle_r = 180 - geometric_angle_r
        
        # =============================================================================
        # LADO IZQUIERDO - EXACTO DE test_elbow_flexion.py
        # =============================================================================
        shoulder_l = landmarks[11]
        elbow_l = landmarks[13]
        wrist_l = landmarks[15]
        
        # Convertir a coordenadas pixel
        shoulder_l_pos = [shoulder_l.x * w, shoulder_l.y * h]
        elbow_l_pos = [elbow_l.x * w, elbow_l.y * h]
        wrist_l_pos = [wrist_l.x * w, wrist_l.y * h]
        
        # 🆕 CALCULAR ÁNGULO GEOMÉTRICO (3 puntos)
        geometric_angle_l = self.calculate_angle_biomechanical(
            shoulder_l_pos, elbow_l_pos, wrist_l_pos
        )
        
        # 🔄 CONVERSIÓN A ÁNGULO CLÍNICO
        angle_l = 180 - geometric_angle_l
        
        # =============================================================================
        # FILTROS (igual que original)
        # =============================================================================
        filtered_angle_r = self.apply_temporal_filter(angle_r, 'right_elbow')
        filtered_angle_l = self.apply_temporal_filter(angle_l, 'left_elbow')
        
        # =============================================================================
        # VALIDACIÓN ANATÓMICA (prevenir ROM imposibles)
        # =============================================================================
        MAX_ELBOW_FLEXION = 160  # Máximo anatómico
        MAX_ELBOW_EXTENSION = 15  # Extensión máxima permitida
        MIN_ELBOW_HYPEREXTENSION = -15  # Hiperextensión máxima
        
        if filtered_angle_r > MAX_ELBOW_FLEXION:
            print(f"⚠️ ROM DERECHO IMPOSIBLE: {filtered_angle_r:.1f}° - Clamping")
            filtered_angle_r = MAX_ELBOW_FLEXION
        elif filtered_angle_r < MIN_ELBOW_HYPEREXTENSION:
            print(f"⚠️ HIPEREXTENSIÓN DERECHA EXCESIVA: {filtered_angle_r:.1f}° - Clamping")
            filtered_angle_r = MIN_ELBOW_HYPEREXTENSION
        
        if filtered_angle_l > MAX_ELBOW_FLEXION:
            print(f"⚠️ ROM IZQUIERDO IMPOSIBLE: {filtered_angle_l:.1f}° - Clamping")
            filtered_angle_l = MAX_ELBOW_FLEXION
        elif filtered_angle_l < MIN_ELBOW_HYPEREXTENSION:
            print(f"⚠️ HIPEREXTENSIÓN IZQUIERDA EXCESIVA: {filtered_angle_l:.1f}° - Clamping")
            filtered_angle_l = MIN_ELBOW_HYPEREXTENSION
        
        # =============================================================================
        # RETURN (estructura compatible con visualización)
        # 🪞 CORRECCIÓN ESPEJO: MediaPipe está en espejo, entonces:
        #    - landmark[12] 'right' = TU brazo IZQUIERDO → guardar como 'left'
        #    - landmark[11] 'left' = TU brazo DERECHO → guardar como 'right'
        # =============================================================================
        return {
            'right_elbow': filtered_angle_l,  # 🪞 INTERCAMBIADO
            'left_elbow': filtered_angle_r,   # 🪞 INTERCAMBIADO
            'raw_right': angle_l,  # 🪞 INTERCAMBIADO
            'raw_left': angle_r,   # 🪞 INTERCAMBIADO
            'positions': {
                'shoulder_r': shoulder_l_pos,  # 🪞 INTERCAMBIADO
                'elbow_r': elbow_l_pos,        # 🪞 INTERCAMBIADO
                'wrist_r': wrist_l_pos,        # 🪞 INTERCAMBIADO
                'shoulder_l': shoulder_r_pos,  # 🪞 INTERCAMBIADO
                'elbow_l': elbow_r_pos,        # 🪞 INTERCAMBIADO
                'wrist_l': wrist_r_pos         # 🪞 INTERCAMBIADO
            },
            'orientation_info': orientation_info
        }
    
    def draw_joint_visualization(self, frame, landmarks, angles):
        """
        ✅ VISUALIZACIÓN SIMPLIFICADA - SOLO estilo de test_elbow_flexion.py
        🎨 Usa vectores verdes/azules, puntos grandes (8px)
        """
        h, w, _ = frame.shape
        
        try:
            # 🧭 DETECTAR QUÉ LADO MOSTRAR - AHORA CON 5 VALORES
            view_type, detected_side, confidence, orientation, facing_direction = self.detect_side_and_visibility(landmarks)
            
            # 🎯 DETERMINAR LADOS A MOSTRAR:
            # - FRONTAL: Mostrar AMBOS lados
            # - PERFIL: Mostrar SOLO el lado detectado
            # 🪞 NOTA: detected_side es landmark ID, pero pos[] ya está intercambiado
            #          detected_side='left' → pos['elbow_r'] tiene datos del brazo derecho usuario
            show_right = False
            show_left = False
            
            if view_type == 'FRONTAL':
                # Mostrar ambos lados
                show_right = True
                show_left = True
            elif view_type == 'SAGITAL':  # FIX 7: SAGITAL no PERFIL
                # Solo el lado detectado
                # 🪞 detected_side='left' (landmark 11) → Usuario muestra brazo derecho → show_right
                # 🪞 detected_side='right' (landmark 12) → Usuario muestra brazo izquierdo → show_left
                if detected_side == 'left':
                    show_right = True  # Brazo derecho del usuario
                    show_left = False
                elif detected_side == 'right':
                    show_right = False
                    show_left = True   # Brazo izquierdo del usuario
                else:
                    # Fallback: mostrar ambos
                    show_right = True
                    show_left = True
            
            # =============================================================================
            # 🎨 DIBUJAR VECTORES Y PUNTOS - ESTILO test_elbow_flexion.py
            # =============================================================================
            
            pos = angles.get('positions', {})
            if not pos:
                return frame
            
            # 📍 CONVERTIR A COORDENADAS INT
            shoulder_r = (int(pos['shoulder_r'][0]), int(pos['shoulder_r'][1])) if pos.get('shoulder_r') else None
            elbow_r = (int(pos['elbow_r'][0]), int(pos['elbow_r'][1])) if pos.get('elbow_r') else None
            wrist_r = (int(pos['wrist_r'][0]), int(pos['wrist_r'][1])) if pos.get('wrist_r') else None
            
            shoulder_l = (int(pos['shoulder_l'][0]), int(pos['shoulder_l'][1])) if pos.get('shoulder_l') else None
            elbow_l = (int(pos['elbow_l'][0]), int(pos['elbow_l'][1])) if pos.get('elbow_l') else None
            wrist_l = (int(pos['wrist_l'][0]), int(pos['wrist_l'][1])) if pos.get('wrist_l') else None
            
            # ✅ BRAZO DERECHO - Solo si está activo
            if show_right and all([shoulder_r, elbow_r, wrist_r]):
                # Puntos clave (GRANDES como test)
                cv2.circle(frame, shoulder_r, 8, (0, 255, 255), -1)  # Amarillo - Hombro
                cv2.circle(frame, elbow_r, 10, (255, 0, 255), -1)    # Magenta - Codo (vértice)
                cv2.circle(frame, wrist_r, 8, (255, 255, 0), -1)     # Cyan - Muñeca
                
                # Líneas (verde brazo superior, azul antebrazo)
                cv2.line(frame, shoulder_r, elbow_r, (0, 255, 0), 3)  # Verde
                cv2.line(frame, elbow_r, wrist_r, (255, 0, 0), 3)     # Azul
                
                # Mostrar ángulo
                angle_value = angles.get('right_elbow', 0)
                angle_text = f"{abs(angle_value):.1f}"
                
                # Texto del ángulo
                cv2.putText(frame, angle_text, 
                           (elbow_r[0] - 40, elbow_r[1] - 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 4)
                
                # Símbolo de grado (círculo pequeño)
                text_width, text_height = cv2.getTextSize(angle_text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 4)[0]
                circle_x = elbow_r[0] - 40 + text_width + 5
                circle_y = elbow_r[1] - 30 - int(text_height * 0.6)
                cv2.putText(frame, "o", (circle_x, circle_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            
            # ✅ BRAZO IZQUIERDO - Solo si está activo
            if show_left and all([shoulder_l, elbow_l, wrist_l]):
                # Puntos clave
                cv2.circle(frame, shoulder_l, 8, (0, 255, 255), -1)  # Amarillo
                cv2.circle(frame, elbow_l, 10, (255, 0, 255), -1)    # Magenta
                cv2.circle(frame, wrist_l, 8, (255, 255, 0), -1)     # Cyan
                
                # Líneas
                cv2.line(frame, shoulder_l, elbow_l, (0, 255, 0), 3)  # Verde
                cv2.line(frame, elbow_l, wrist_l, (255, 0, 0), 3)     # Azul
                
                # Mostrar ángulo
                angle_value = angles.get('left_elbow', 0)
                angle_text = f"{abs(angle_value):.1f}"
                
                cv2.putText(frame, angle_text, 
                           (elbow_l[0] - 40, elbow_l[1] - 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 4)
                
                # Símbolo de grado
                text_width, text_height = cv2.getTextSize(angle_text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 4)[0]
                circle_x = elbow_l[0] - 40 + text_width + 5
                circle_y = elbow_l[1] - 30 - int(text_height * 0.6)
                cv2.putText(frame, "o", (circle_x, circle_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            
            return frame
                
        except Exception as e:
            print(f"❌ Error en visualización de codo: {e}")
            return frame
    
    def _draw_orientation_info(self, frame, orientation_info):
        """🧭 Mostrar información de orientación simple"""
        if not orientation_info:
            return frame
        
        orientation = orientation_info.get('orientation', 'UNKNOWN')
        confidence = orientation_info.get('confidence', 0)
        
        # Información básica de orientación
        #cv2.putText(frame, f"Orientacion: {orientation}", 
                   # (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        # if confidence > 0:
            # cv2.putText(frame, f"Confianza: {confidence:.1f}%", 
                       # (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (100, 255, 100), 1)
        
        return frame
    
    def _assess_elbow_range(self, angle, side):
        """📊 Evaluación clínica del rango de codo"""
        
        # Rangos normales del codo
        if angle <= 20:  # Extensión
            if angle <= 5:
                status = "EXCELLENT"
                recommendation = "Extensión completa lograda"
            else:
                status = "GOOD" 
                recommendation = "Extensión casi completa"
            movement = "extension"
            
        elif angle >= 120:  # Flexión completa
            if angle >= 140:
                status = "EXCELLENT"
                recommendation = f"Flexión óptima ({angle:.0f}°)"
            else:
                status = "GOOD"
                recommendation = "Buena flexión"
            movement = "flexion"
            
        elif angle >= 90:  # Flexión moderada
            status = "FAIR"
            recommendation = "Flexión moderada - puede mejorar"
            movement = "flexion"
            
        else:  # Rango intermedio (30-90°)
            status = "NEUTRAL"
            recommendation = "Rango intermedio"
            movement = "intermediate"
        
        return {
            "status": status,
            "movement": movement,
            "recommendation": recommendation,
            "angle": angle,
            "side": side,
            "percentage": min(100, (angle / 150) * 100)
        }

    def get_movement_type(self, angle):
        """🎯 Determinar tipo de movimiento del codo"""
        if angle <= 20:
            return "extension"
        elif angle >= 90:
            return "flexion" 
        else:
            return "intermediate"
    
    def _select_best_arm(self, landmarks, current_orientation="UNKNOWN"):
        """🎯 Seleccionar el brazo óptimo según orientación y visibilidad"""
        
        left_arm_points = [11, 13, 15]   # Hombro, codo, muñeca izquierda
        right_arm_points = [12, 14, 16]  # Hombro, codo, muñeca derecha
        
        # 🧭 LÓGICA ESPECÍFICA POR ORIENTACIÓN
        if current_orientation == "SAGITAL":
            return self._select_arm_for_sagittal_view(landmarks, left_arm_points, right_arm_points)
        else:
            return self._select_arm_for_frontal_view(landmarks, left_arm_points, right_arm_points)

    def _select_arm_for_sagittal_view(self, landmarks, left_points, right_points):
        """🎯 Selección inteligente para vista SAGITAL (perfil)"""
        
        # En vista sagital, detectar qué lado está visible
        # Analizar posición relativa de los hombros
        if len(landmarks) > 12:
            l_shoulder = landmarks[11]
            r_shoulder = landmarks[12]
            
            # 📏 DETERMINAR QUE LADO ESTÁ MÁS VISIBLE
            # En sagital, uno de los hombros estará más "adelante" (menor X o mayor X)
            shoulder_diff_x = abs(l_shoulder.x - r_shoulder.x)
            
            print(f"🔍 SAGITAL DEBUG: Diferencia X hombros = {shoulder_diff_x:.3f}")
            
            # Si los hombros están muy alineados en X, es vista sagital pura
            if shoulder_diff_x < 0.1:  # Hombros superpuestos en vista sagital
                # Seleccionar el brazo con mejor visibilidad TOTAL
                left_arm_data = self._evaluate_arm_visibility(landmarks, left_points, "LEFT")
                right_arm_data = self._evaluate_arm_visibility(landmarks, right_points, "RIGHT")
                
                print(f"🔍 SAGITAL: Brazo izq score={left_arm_data['score']:.2f}, der score={right_arm_data['score']:.2f}")
                
                # En sagital, preferir el brazo que esté MÁS COMPLETO
                if left_arm_data['complete_points'] > right_arm_data['complete_points']:
                    return left_arm_data
                elif right_arm_data['complete_points'] > left_arm_data['complete_points']:
                    return right_arm_data
                else:
                    # Si igual completitud, usar el de mejor score
                    return left_arm_data if left_arm_data['score'] >= right_arm_data['score'] else right_arm_data
            
            else:
                # Vista no completamente sagital - usar método normal
                return self._select_arm_for_frontal_view(landmarks, left_points, right_points)
        
        # Fallback si no hay suficientes landmarks
        return {"valid": False, "reason": "Insufficient landmarks for sagittal analysis"}

    def _select_arm_for_frontal_view(self, landmarks, left_points, right_points):
        """🎯 Selección para vista FRONTAL (método original mejorado)"""
        
        left_arm_data = self._evaluate_arm_visibility(landmarks, left_points, "LEFT")
        right_arm_data = self._evaluate_arm_visibility(landmarks, right_points, "RIGHT")
        
        # Seleccionar el brazo con mejor puntuación
        if left_arm_data['score'] >= 2.1 and left_arm_data['complete_points'] == 3:
            return left_arm_data
        elif right_arm_data['score'] >= 2.1 and right_arm_data['complete_points'] == 3:
            return right_arm_data
        elif left_arm_data['score'] >= right_arm_data['score']:
            return left_arm_data
        else:
            return right_arm_data

    def _evaluate_arm_visibility(self, landmarks, arm_points, side_name):
        """📊 Evaluar visibilidad completa de un brazo - MÁS FLEXIBLE"""
        
        score = 0
        landmarks_dict = {}
        complete_points = 0
        
        point_names = ['shoulder', 'elbow', 'wrist']
        
        for i, point_id in enumerate(arm_points):
            if point_id < len(landmarks):
                visibility = landmarks[point_id].visibility
                # ✅ UMBRAL MÁS BAJO Y FLEXIBLE
                if visibility > 0.4:  # Cambiado de 0.6 a 0.4
                    score += visibility
                    landmarks_dict[point_names[i]] = landmarks[point_id]
                    complete_points += 1
        
        return {
            "valid": complete_points >= 2,  # ✅ 2 de 3 puntos suficientes
            "side": side_name,
            "landmarks": landmarks_dict,
            "score": score,
            "complete_points": complete_points,
            "points": arm_points,
            "reason": f"{complete_points}/3 points visible, score={score:.2f}"
        }
    
    def _analyze_single_arm(self, landmarks, arm_side, w, h, orientation):
        """
        🦴 Analizar UN brazo independientemente
        🔧 FIX #13: Ahora usa método científico (fixed_reference) igual que shoulder
        """
        
        # 📍 ÍNDICES DE PUNTOS
        if arm_side == "RIGHT":
            indices = [12, 14, 16]  # Hombro, codo, muñeca derecha
        else:  # LEFT
            indices = [11, 13, 15]  # Hombro, codo, muñeca izquierda
        
        # 🔍 UMBRALES DINÁMICOS
        if orientation == "SAGITAL":
            min_visibility = 0.4
            required_points = 2  # Flexibilidad en sagital
        else:
            min_visibility = 0.6
            required_points = 3  # Estricto en frontal
        
        # 📊 EXTRAER PUNTOS CON VALIDACIÓN
        points = {}
        valid_count = 0
        point_names = ['shoulder', 'elbow', 'wrist']
        
        for i, idx in enumerate(indices):
            if idx < len(landmarks):
                landmark = landmarks[idx]
                if landmark.visibility > min_visibility:
                    points[point_names[i]] = (int(landmark.x * w), int(landmark.y * h))
                    valid_count += 1
                else:
                    points[point_names[i]] = None
            else:
                points[point_names[i]] = None
        
        # ✅ VERIFICAR SI ES CALCULABLE
        essential_points = [points['shoulder'], points['elbow'], points['wrist']]
        
        if valid_count >= required_points and all(p is not None for p in essential_points):
            # 📐 CALCULAR ÁNGULO CON MÉTODO 3 PUNTOS (científico correcto para codo)
            # 🎯 CODO es articulación DISTAL → se mide respecto a segmento proximal (brazo superior)
            # 🔬 Norkin & White (2016): "Flexión de codo = ángulo entre húmero y radio"
            # ✅ Método: hombro-codo-muñeca (NO antebrazo vs vertical)
            
            # 🎯 CALCULAR ÁNGULO GEOMÉTRICO (3 puntos)
            geometric_angle = self.calculate_angle_biomechanical(
                points['shoulder'],  # Punto 1: hombro (proximal)
                points['elbow'],     # Punto 2: codo (vértice)
                points['wrist']      # Punto 3: muñeca (distal)
            )
            
            # 🔄 CONVERSIÓN A ÁNGULO CLÍNICO (goniométrico)
            # Ángulo geométrico: 180° = extensión, 35° = flexión máxima
            # Ángulo clínico: 0° = extensión, 145° = flexión máxima
            raw_angle = 180 - geometric_angle
            
            return {
                'status': 'VALID',
                'angle': raw_angle,
                'raw_angle': raw_angle,
                'quality': valid_count,
                'points': points
            }
        else:
            # ❌ INSUFICIENTES PUNTOS
            return {
                'status': 'INSUFFICIENT',
                'angle': 0.0,
                'raw_angle': 0.0,
                'quality': valid_count,
                'points': {k: None for k in point_names}
            }

    def _select_primary_arm_for_sagittal(self, right_result, left_result):
        """🎯 Seleccionar el brazo principal en vista SAGITAL"""
        
        right_valid = right_result['status'] == 'VALID'
        left_valid = left_result['status'] == 'VALID'
        
        if right_valid and not left_valid:
            return "RIGHT"
        elif left_valid and not right_valid:
            return "LEFT" 
        elif right_valid and left_valid:
            # Ambos válidos: elegir el de mejor calidad
            if right_result['quality'] >= left_result['quality']:
                return "RIGHT"
            else:
                return "LEFT"
        else:
            return "NONE"  # Ninguno válido

    def _get_default_result(self):
        """📊 Resultado por defecto"""
        return {
            'right_elbow': 0, 'left_elbow': 0, 'raw_right': 0, 'raw_left': 0,
            'positions': {k: None for k in ['shoulder_r', 'elbow_r', 'wrist_r', 'shoulder_l', 'elbow_l', 'wrist_l']},
            'orientation_info': {'orientation': 'UNKNOWN'},
            'primary_arm': 'NONE', 'right_arm_quality': 0, 'left_arm_quality': 0
        }
    
    def check_required_points_visible(self, landmarks):
        """
        🛡️ VALIDACIÓN ADAPTATIVA según CAMERA_ORIENTATION del JSON
        ✅ IGUAL QUE SHOULDER - usa self.current_camera_orientation
        """
        if not landmarks or len(landmarks) < 16:
            return False
        
        # 🎯 USAR ORIENTACIÓN DEL JSON (ya establecida en set_current_exercise)
        is_sagital = self.current_camera_orientation == 'sagital'
        
        if is_sagital:
            # 🔄 SAGITAL: Solo requiere hombros + codos de UN brazo
            required_points = [11, 12, 13, 14]  # Hombros y codos
            threshold = 0.3  # MUY BAJO para cámaras de baja calidad
            min_visible = 3  # Al menos 3 de 4
        else:
            # FRONTAL: Requiere ambos brazos visibles
            required_points = [11, 12, 13, 14, 15, 16]  # Hombros, codos, muñecas
            threshold = 0.5
            min_visible = 4  # Al menos 4 de 6
        
        # 📊 CONTAR PUNTOS VISIBLES
        visible_count = sum(
            1 for idx in required_points
            if idx < len(landmarks) and landmarks[idx].visibility > threshold
        )
        
        is_valid = visible_count >= min_visible
        
        # 🔇 Solo log si hay cambio de estado (evitar spam)
        if not hasattr(self, '_last_visibility_state') or self._last_visibility_state != is_valid:
            print(f"🎯 Visibilidad {self.current_camera_orientation.upper()}: {visible_count}/{len(required_points)} puntos → {'✅ VÁLIDO' if is_valid else '❌ INVÁLIDO'}")
            self._last_visibility_state = is_valid
        
        return is_valid

    
    def _get_stable_orientation(self, landmarks):
        """🧭 Orientación ESTABLE - no cambia constantemente"""
        
        try:
            # 🔄 COOLDOWN para evitar cambios muy frecuentes
            if self.orientation_change_cooldown > 0:
                self.orientation_change_cooldown -= 1
                return self.current_stable_orientation
            
            # Detectar orientación actual
            orientation_info = self.orientation_detector.detect_orientation_adaptive(landmarks)
            detected = orientation_info.get('orientation', 'UNKNOWN')
            
            # Agregar al historial
            self.orientation_history.append(detected)
            
            # Mantener solo últimas 8 detecciones
            if len(self.orientation_history) > 8:
                self.orientation_history.pop(0)
            
            # Cambiar orientación solo si hay consenso fuerte (6 de 8)
            if len(self.orientation_history) >= 6:
                sagital_count = self.orientation_history.count("SAGITAL")
                frontal_count = self.orientation_history.count("FRONTAL")
                
                if sagital_count >= 6 and self.current_stable_orientation != "SAGITAL":
                    print("🔄 CAMBIO: FRONTAL → SAGITAL")
                    self.current_stable_orientation = "SAGITAL"
                    self.orientation_change_cooldown = 15  # 15 frames sin cambios
                elif frontal_count >= 6 and self.current_stable_orientation != "FRONTAL":
                    print("🔄 CAMBIO: SAGITAL → FRONTAL") 
                    self.current_stable_orientation = "FRONTAL"
                    self.orientation_change_cooldown = 15  # 15 frames sin cambios
            
            return self.current_stable_orientation
        
        except Exception as e:
            print(f"⚠️ Error orientación estable: {e}")
            return self.current_stable_orientation
    
    # ========================================================================
    # 🆕 NUEVOS MÉTODOS: DETECCIÓN PERFIL Z + UNILATERAL CIENTÍFICO
    # ========================================================================
    
    def _detect_true_profile(self, landmarks, w, h):
        """
        🎯 DETECTAR PERFIL VERDADERO usando PROFUNDIDAD Z
        ✅ USA HELPER UTILITY centralizado (mismo que shoulder)
        
        DIFERENCIA CON SHOULDER: Usa CODO como referencia proximal (no hombro)
        
        Returns: ('RIGHT', 'LEFT', 'BILATERAL', 'NONE')
        """
        from biomechanical_analysis.utils.profile_detection import (
            detect_profile_by_z_depth,
            get_z_threshold_for_joint
        )
        
        # 📐 PUNTOS ANATÓMICOS ESPECÍFICOS DE CODO
        # Distal: muñecas [15/16]
        # Proximal: CODOS [13/14] (NO hombros - diferencia clave con shoulder)
        wrist_r = landmarks[16]
        wrist_l = landmarks[15]
        elbow_r = landmarks[14]  # ⚠️ CRÍTICO: Usar codo, no hombro
        elbow_l = landmarks[13]  # ⚠️ CRÍTICO: Usar codo, no hombro
        
        # 🎯 USAR HELPER UTILITY con threshold específico para codo
        z_threshold = get_z_threshold_for_joint('elbow')  # 0.25 (mismo que shoulder)
        
        return detect_profile_by_z_depth(
            point_distal_r=wrist_r,
            point_distal_l=wrist_l,
            point_proximal_r=elbow_r,  # CODO como referencia
            point_proximal_l=elbow_l,  # CODO como referencia
            z_threshold=z_threshold,
            vis_threshold=0.4,
            debug=True  # Mantener logs para debugging
        )
    
    def _calculate_unilateral_profile_scientific(self, landmarks, w, h, orientation_info, side):
        """
        🆕 MÉTODO CIENTÍFICO UNILATERAL para perfil verdadero (CODO)
        📐 Calcula SOLO el lado visible con método científico (codo→muñeca vs vertical)
        
        DIFERENCIA CON SHOULDER: 
        - Segmento: CODO→muñeca (no hombro→muñeca)
        - Ejercicio key: elbow_{exercise} (no shoulder_{exercise})
        
        Args:
            side: 'RIGHT' o 'LEFT' - indica qué lado está visible
        """
        from core.fixed_references import FixedSpatialReferences
        
        ref_system = FixedSpatialReferences()
        orientation = 'SAGITAL'  # Perfil siempre es sagital
        visibility_threshold = 0.3  # Tolerante para perfil
        
        if side == 'RIGHT':
            # 📐 LADO DERECHO visible
            shoulder = landmarks[12]
            elbow = landmarks[14]
            wrist = landmarks[16]
            
            # 🔬 MÉTODO 3 PUNTOS (hombro-codo-muñeca) - CORRECTO para articulación distal
            if elbow.visibility > visibility_threshold and wrist.visibility > visibility_threshold and shoulder.visibility > visibility_threshold:
                # Convertir landmarks a tuples (x_pixel, y_pixel)
                shoulder_px = (shoulder.x * w, shoulder.y * h)
                elbow_px = (elbow.x * w, elbow.y * h)
                wrist_px = (wrist.x * w, wrist.y * h)
                
                # Calcular ángulo geométrico
                geometric_angle = self.calculate_angle_biomechanical(
                    shoulder_px, elbow_px, wrist_px
                )
                
                # Conversión a ángulo clínico
                angle = 180 - geometric_angle
            else:
                angle = 0
            
            # Filtrar
            filtered_angle = self.apply_temporal_filter(angle, 'right_elbow_unilateral')
            
            # 🆕 VALIDACIÓN ANATÓMICA (Norkin & White 2016: rango normal 0-150°)
            MAX_ELBOW_ROM = 155  # Límite conservador (incluye hipermobilidad leve)
            if filtered_angle > MAX_ELBOW_ROM:
                # Cache warning para no spamear logs
                if not hasattr(self, '_last_rom_warning_right') or self._last_rom_warning_right != filtered_angle:
                    print(f"⚠️ ROM DERECHO imposible: {filtered_angle:.1f}° > {MAX_ELBOW_ROM}° - Clamping")
                    self._last_rom_warning_right = filtered_angle
                filtered_angle = MAX_ELBOW_ROM
            elif filtered_angle < -15:
                if not hasattr(self, '_last_hyperext_warning_right') or abs(self._last_hyperext_warning_right - filtered_angle) > 2:
                    print(f"⚠️ HIPEREXTENSIÓN DERECHA excesiva: {filtered_angle:.1f}° - Clamping")
                    self._last_hyperext_warning_right = filtered_angle
                filtered_angle = -15
            
            return {
                'analysis_mode': 'UNILATERAL_PROFILE_RIGHT',
                'right_elbow': filtered_angle,
                'left_elbow': 0,  # Lado oculto
                'raw_right': angle,
                'raw_left': 0,
                'positions': {
                    # Lado derecho visible
                    'shoulder_r': [shoulder.x * w, shoulder.y * h],
                    'elbow_r': [elbow.x * w, elbow.y * h],
                    'wrist_r': [wrist.x * w, wrist.y * h],
                    # Lado izquierdo: None (no dibujar)
                    'shoulder_l': None,
                    'elbow_l': None,
                    'wrist_l': None
                },
                'orientation_info': orientation_info,
                'primary_arm': 'RIGHT',
                'right_arm_quality': 'EXCELLENT',
                'left_arm_quality': 'HIDDEN'
            }
            
        elif side == 'LEFT':
            # 📐 LADO IZQUIERDO visible
            shoulder = landmarks[11]
            elbow = landmarks[13]
            wrist = landmarks[15]
            
            # 🔬 MÉTODO 3 PUNTOS (hombro-codo-muñeca) - CORRECTO para articulación distal
            if elbow.visibility > visibility_threshold and wrist.visibility > visibility_threshold and shoulder.visibility > visibility_threshold:
                # Convertir landmarks a tuples (x_pixel, y_pixel)
                shoulder_px = (shoulder.x * w, shoulder.y * h)
                elbow_px = (elbow.x * w, elbow.y * h)
                wrist_px = (wrist.x * w, wrist.y * h)
                
                # Calcular ángulo geométrico
                geometric_angle = self.calculate_angle_biomechanical(
                    shoulder_px, elbow_px, wrist_px
                )
                
                # Conversión a ángulo clínico
                angle = 180 - geometric_angle
            else:
                angle = 0
            
            # Filtrar
            filtered_angle = self.apply_temporal_filter(angle, 'left_elbow_unilateral')
            
            # 🆕 VALIDACIÓN ANATÓMICA (Norkin & White 2016: rango normal 0-150°)
            MAX_ELBOW_ROM = 155  # Límite conservador (incluye hipermobilidad leve)
            if filtered_angle > MAX_ELBOW_ROM:
                # Cache warning para no spamear logs
                if not hasattr(self, '_last_rom_warning_left') or self._last_rom_warning_left != filtered_angle:
                    print(f"⚠️ ROM IZQUIERDO imposible: {filtered_angle:.1f}° > {MAX_ELBOW_ROM}° - Clamping")
                    self._last_rom_warning_left = filtered_angle
                filtered_angle = MAX_ELBOW_ROM
            elif filtered_angle < -15:
                if not hasattr(self, '_last_hyperext_warning_left') or abs(self._last_hyperext_warning_left - filtered_angle) > 2:
                    print(f"⚠️ HIPEREXTENSIÓN IZQUIERDA excesiva: {filtered_angle:.1f}° - Clamping")
                    self._last_hyperext_warning_left = filtered_angle
                filtered_angle = -15
            
            return {
                'analysis_mode': 'UNILATERAL_PROFILE_LEFT',
                'right_elbow': 0,  # Lado oculto
                'left_elbow': filtered_angle,
                'raw_right': 0,
                'raw_left': angle,
                'positions': {
                    # Lado derecho: None (no dibujar)
                    'shoulder_r': None,
                    'elbow_r': None,
                    'wrist_r': None,
                    # Lado izquierdo visible
                    'shoulder_l': [shoulder.x * w, shoulder.y * h],
                    'elbow_l': [elbow.x * w, elbow.y * h],
                    'wrist_l': [wrist.x * w, wrist.y * h]
                },
                'orientation_info': orientation_info,
                'primary_arm': 'LEFT',
                'right_arm_quality': 'HIDDEN',
                'left_arm_quality': 'EXCELLENT'
            }
        
        else:
            # Error: lado no reconocido
            print(f"❌ ERROR: Lado '{side}' no reconocido")
            return self._get_default_result()
    
    def _draw_unilateral_profile_visualization(self, frame, landmarks, angles, w, h):
        """
        🆕 VISUALIZACIÓN UNILATERAL CIENTÍFICA para perfil verdadero (CODO)
        📐 Dibuja SOLO el lado visible: 1 eje amarillo + 1 arco verde + texto
        ✅ SIN dibujar el lado oculto (sin [0,0])
        
        SIMILAR A SHOULDER pero con etiquetas "CODO" y landmarks específicos
        """
        analysis_mode = angles.get('analysis_mode', '')
        pos = angles.get('positions', {})
        
        # 🔍 DEBUG con cache (se ejecuta cada frame = 30 veces/seg)
        cache_key = f"{analysis_mode}_{','.join(pos.keys())}"
        if not hasattr(self, '_last_draw_debug') or self._last_draw_debug != cache_key:
            print(f"🎨 [ELBOW _draw_unilateral] mode={analysis_mode}, positions={list(pos.keys())}")
            self._last_draw_debug = cache_key
        
        # Dibujar esqueleto SOLO del lado visible
        if 'RIGHT' in analysis_mode and pos.get('elbow_r') is not None:
            # 📐 LADO DERECHO visible
            shoulder_r_landmark = landmarks[12]
            elbow_r_landmark = landmarks[14]
            wrist_r_landmark = landmarks[16]
            
            # Conexiones del lado derecho
            cv2.line(frame, 
                    (int(shoulder_r_landmark.x * w), int(shoulder_r_landmark.y * h)),
                    (int(elbow_r_landmark.x * w), int(elbow_r_landmark.y * h)),
                    (0, 255, 0), 3)  # Verde - Hombro-codo
            cv2.line(frame,
                    (int(elbow_r_landmark.x * w), int(elbow_r_landmark.y * h)),
                    (int(wrist_r_landmark.x * w), int(wrist_r_landmark.y * h)),
                    (0, 255, 0), 3)  # Verde - Codo-muñeca
            
            # 🟡 EJE BRAZO SUPERIOR AMARILLO (hombro→codo) - Vector fijo del método 3 puntos
            elbow_int = (int(pos['elbow_r'][0]), int(pos['elbow_r'][1]))
            if pos.get('shoulder_r'):
                shoulder_int = (int(pos['shoulder_r'][0]), int(pos['shoulder_r'][1]))
                # Vector brazo superior
                vec_brazo_superior = {
                    'x': pos['elbow_r'][0] - pos['shoulder_r'][0],
                    'y': pos['elbow_r'][1] - pos['shoulder_r'][1]
                }
                # Normalizar y extender para visualización
                mag = math.sqrt(vec_brazo_superior['x']**2 + vec_brazo_superior['y']**2)
                if mag > 0:
                    vec_norm = {'x': vec_brazo_superior['x']/mag, 'y': vec_brazo_superior['y']/mag}
                    brazo_end = (
                        elbow_int[0] + int(vec_norm['x'] * 150),
                        elbow_int[1] + int(vec_norm['y'] * 150)
                    )
                    cv2.line(frame, elbow_int, brazo_end, (0, 255, 255), 10)
            
            # 🟢 ARCO VERDE científico (brazo superior vs antebrazo) - Método 3 puntos CORRECTO
            if pos.get('wrist_r') and pos.get('shoulder_r'):
                # Vector brazo superior (hombro→codo)
                vec_brazo_superior = {
                    'x': pos['elbow_r'][0] - pos['shoulder_r'][0],
                    'y': pos['elbow_r'][1] - pos['shoulder_r'][1]
                }
                # Vector antebrazo (codo→muñeca)
                vec_antebrazo = {
                    'x': pos['wrist_r'][0] - pos['elbow_r'][0],
                    'y': pos['wrist_r'][1] - pos['elbow_r'][1]
                }
                
                # Reutilizar helper de arcos
                frame = self._draw_arc_between_vectors(
                    frame,
                    pos['elbow_r'],
                    vec_brazo_superior,  # Vector 1: brazo superior
                    vec_antebrazo,       # Vector 2: antebrazo
                    angles['right_elbow'],
                    radius=80,
                    color=(0, 255, 0),  # Verde
                    thickness=8
                )
            
            # 🏷️ ETIQUETAS
            cv2.circle(frame, elbow_int, 10, (255, 0, 128), -1)
            #cv2.putText(frame, "CODO DER", (elbow_int[0]-40, elbow_int[1]-15),
                       #cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 128), 2)
            
            # 📊 TEXTO CIENTÍFICO
            frame = self.add_text_with_pillow(frame,
                f"📐 PERFIL DERECHO: {angles['right_elbow']:.0f}° (3 puntos: hombro-codo-muñeca)",
                (10, 40), font_size=18, color=(0, 255, 0))
            
        elif 'LEFT' in analysis_mode and pos.get('elbow_l') is not None:
            # 📐 LADO IZQUIERDO visible
            shoulder_l_landmark = landmarks[11]
            elbow_l_landmark = landmarks[13]
            wrist_l_landmark = landmarks[15]
            
            # Conexiones del lado izquierdo
            cv2.line(frame,
                    (int(shoulder_l_landmark.x * w), int(shoulder_l_landmark.y * h)),
                    (int(elbow_l_landmark.x * w), int(elbow_l_landmark.y * h)),
                    (0, 255, 0), 3)
            cv2.line(frame,
                    (int(elbow_l_landmark.x * w), int(elbow_l_landmark.y * h)),
                    (int(wrist_l_landmark.x * w), int(wrist_l_landmark.y * h)),
                    (0, 255, 0), 3)
            
            # 🟡 EJE BRAZO SUPERIOR AMARILLO (hombro→codo) - Vector fijo del método 3 puntos
            elbow_int = (int(pos['elbow_l'][0]), int(pos['elbow_l'][1]))
            if pos.get('shoulder_l'):
                shoulder_int = (int(pos['shoulder_l'][0]), int(pos['shoulder_l'][1]))
                # Vector brazo superior
                vec_brazo_superior = {
                    'x': pos['elbow_l'][0] - pos['shoulder_l'][0],
                    'y': pos['elbow_l'][1] - pos['shoulder_l'][1]
                }
                # Normalizar y extender para visualización
                mag = math.sqrt(vec_brazo_superior['x']**2 + vec_brazo_superior['y']**2)
                if mag > 0:
                    vec_norm = {'x': vec_brazo_superior['x']/mag, 'y': vec_brazo_superior['y']/mag}
                    brazo_end = (
                        elbow_int[0] + int(vec_norm['x'] * 150),
                        elbow_int[1] + int(vec_norm['y'] * 150)
                    )
                    cv2.line(frame, elbow_int, brazo_end, (0, 255, 255), 10)
            
            # 🟢 ARCO VERDE científico (brazo superior vs antebrazo) - Método 3 puntos CORRECTO
            if pos.get('wrist_l') and pos.get('shoulder_l'):
                # Vector brazo superior (hombro→codo)
                vec_brazo_superior = {
                    'x': pos['elbow_l'][0] - pos['shoulder_l'][0],
                    'y': pos['elbow_l'][1] - pos['shoulder_l'][1]
                }
                # Vector antebrazo (codo→muñeca)
                vec_antebrazo = {
                    'x': pos['wrist_l'][0] - pos['elbow_l'][0],
                    'y': pos['wrist_l'][1] - pos['elbow_l'][1]
                }
                
                frame = self._draw_arc_between_vectors(
                    frame,
                    pos['elbow_l'],
                    vec_brazo_superior,  # Vector 1: brazo superior
                    vec_antebrazo,       # Vector 2: antebrazo
                    angles['left_elbow'],
                    radius=80,
                    color=(0, 255, 0),
                    thickness=8
                )
            
            # 🏷️ ETIQUETAS
            cv2.circle(frame, elbow_int, 10, (128, 0, 255), -1)
            # cv2.putText(frame, "CODO IZQ", (elbow_int[0]-40, elbow_int[1]-15),
                       # cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 0, 255), 2)
            
            # 📊 TEXTO CIENTÍFICO
            frame = self.add_text_with_pillow(frame,
                f"📐 PERFIL IZQUIERDO: {angles['left_elbow']:.0f}° (3 puntos: hombro-codo-muñeca)",
                (10, 40), font_size=18, color=(0, 255, 0))
        
        # ℹ️ Indicador de modo
        # cv2.putText(frame, "MODO: PERFIL UNILATERAL CODO (Cientifico)", (10, h - 20),
                   # cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame
    
    def _draw_arc_between_vectors(self, frame, origin, vec_movil, vec_fixed, angle, radius=40, color=(0, 255, 0), thickness=3):
        """
        🆕 HELPER: Dibuja arco entre vector móvil (antebrazo) y vector fijo (vertical)
        ✅ IDÉNTICO al de shoulder_analyzer (reutilizar lógica)
        """
        try:
            import math
            
            # 📐 Calcular ángulos en radianes desde el eje X positivo
            angle_movil = math.atan2(vec_movil['y'], vec_movil['x'])
            angle_fixed = math.atan2(vec_fixed['y'], vec_fixed['x'])
            
            # 🔄 Convertir a grados
            angle_movil_deg = math.degrees(angle_movil)
            angle_fixed_deg = math.degrees(angle_fixed)
            
            # 🎯 Asegurar que angle_fixed < angle_movil para cv2.ellipse
            if angle_fixed_deg > angle_movil_deg:
                angle_movil_deg, angle_fixed_deg = angle_fixed_deg, angle_movil_deg
            
            # 🎨 Dibujar arco con cv2.ellipse
            cv2.ellipse(
                frame, 
                tuple(map(int, origin)),  # Centro del arco (codo)
                (radius, radius),          # Ejes del arco (circular)
                0,                         # Rotación (0 = sin rotar)
                angle_fixed_deg,           # Ángulo inicial (referencia fija)
                angle_movil_deg,           # Ángulo final (vector antebrazo)
                color,                     # Color
                thickness                  # Grosor
            )
            
            return frame
            
        except Exception as e:
            # 🛡️ Silencioso: No romper visualización si arco falla
            print(f"⚠️ Error dibujando arco científico (elbow): {e}")
            return frame