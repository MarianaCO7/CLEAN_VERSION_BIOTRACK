import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_analyzer import BaseJointAnalyzer
from core.orientation_detector import AdaptiveOrientationDetector
from core.fixed_references import FixedSpatialReferences  # 🚀 IMPORT UNA SOLA VEZ (no cada frame)
import cv2
import numpy as np
import math
import json
import os

class ShoulderAnalyzer(BaseJointAnalyzer):
    """
    🦴 ANALIZADOR DE HOMBRO CONSERVADOR
    🛡️ PRIORIZA análisis bilateral, fallback SOLO en casos extremos
    """
    
    def __init__(self):
        super().__init__("Shoulder")
        
        # ✅ MANTENER configuración existente
        self.orientation_detector = AdaptiveOrientationDetector()
        
        # ✅ AGREGAR: Configuración dinámica de ejercicios
        self.exercise_configs = self._load_exercise_configs()
        self.current_exercise = 'flexion'  # Default para compatibilidad
        self.current_camera_orientation = 'sagital'  # 🆕 Default: sagital (flexión/extensión)
        
        # 🎨 FASE 3: Flag para visualización mejorada (arcos científicos)
        self.ENHANCED_VISUALIZATION = True  # ✅ Toggle: True = arcos científicos, False = fallback a original
        
        print(f"✅ ShoulderAnalyzer inicializado con {len(self.exercise_configs)} ejercicios")
        print(f"🎨 FASE 3: ENHANCED_VISUALIZATION = {self.ENHANCED_VISUALIZATION}")
    
    def _load_exercise_configs(self):
        """📋 Cargar configuraciones de ejercicios de hombro"""
        try:
            # ✅ Buscar archivo de configuración
            current_dir = os.path.dirname(__file__)
            config_path = os.path.join(current_dir, '..', '..', 
                                      'biomechanical_web_interface', 'config', 'exercises.json')
            
            if not os.path.exists(config_path):
                print(f"⚠️ Archivo exercises.json no encontrado, usando configuración por defecto")
                return self._get_default_config()
            
            with open(config_path, 'r', encoding='utf-8') as f:
                configs = json.load(f)
            
            shoulder_exercises = configs['segments']['shoulder']['exercises']
            print(f"✅ Configuración cargada: {list(shoulder_exercises.keys())}")
            return shoulder_exercises
            
        except Exception as e:
            print(f"⚠️ Error cargando configuración: {e}, usando configuración por defecto")
            return self._get_default_config()
    
    def _get_default_config(self):
        """🔄 Configuración por defecto si no se puede cargar JSON"""
        return {
            'flexion': {
                'name': 'Flexión de Hombro',
                'calculation_method': 'flexion_sagital',
                'normal_range': {'min': 0, 'max': 180}
            }
        }
    
    def set_current_exercise(self, exercise_type):
        """🎯 Establecer ejercicio actual para análisis"""
        if exercise_type in self.exercise_configs:
            self.current_exercise = exercise_type
            
            # 🆕 CARGAR camera_orientation desde config JSON
            self.current_camera_orientation = self.exercise_configs[exercise_type].get('camera_orientation', 'sagital')
            
            print(f"✅ Ejercicio establecido: {exercise_type}")
            print(f"📷 Orientación de cámara requerida: {self.current_camera_orientation}")
        else:
            print(f"⚠️ Ejercicio {exercise_type} no válido, manteniendo {self.current_exercise}")
    
    def get_required_landmarks(self):
        return [11, 12, 13, 14, 23, 24]
    
    def check_required_points_visible(self, landmarks):
        """
        🛡️ VALIDACIÓN ADAPTATIVA según ejercicio
        - Frontal (abducción): threshold 0.5 tolerante (requiere 4/4 puntos)
        - Sagital (flexión/perfil): threshold 0.3 MUY tolerante (solo hombros+codos)
        """
        # 🎯 DETECCIÓN RÁPIDA: ¿Qué ejercicio estamos haciendo?
        # Si es flexión/extensión (perfil), ser MUY tolerante
        is_profile_exercise = self.current_exercise in ['flexion', 'extension']
        is_frontal_exercise = self.current_exercise in ['abduction', 'abduccion']  # 🆕 Inglés Y español
        
        if is_profile_exercise:
            # 🔄 PERFIL: Solo requiere hombros + codos visibles (threshold 0.3 - MUY BAJO)
            # Las caderas pueden estar parcialmente ocultas de perfil
            profile_required = [11, 12, 13, 14]  # Hombros y codos solamente
            threshold = 0.3  # 🆕 BAJADO de 0.4 a 0.3 para menos fallos intermitentes
            
            # 🆕 VALIDACIÓN FLEXIBLE: Al menos 3 de 4 puntos deben estar visibles
            visible_count = sum(
                1 for i in profile_required 
                if len(landmarks) > i and landmarks[i].visibility > threshold
            )
            
            if visible_count >= 3:  # Al menos 3 de 4 (hombros son más críticos)
                # print(f"   ✅ Validación PERFIL: {visible_count}/4 puntos visibles (threshold={threshold})")  # 🔇 Comentado - performance
                return True
            else:
                # print(f"   ⚠️ Validación PERFIL FALLIDA: solo {visible_count}/4 puntos visibles")  # 🔇 Comentado - performance
                return False
        
        elif is_frontal_exercise:
            # 🆕 VALIDACIÓN ESPECÍFICA PARA FRONTAL (ABDUCCIÓN)
            # Solo requiere hombros + codos, con threshold más bajo (0.4)
            # No incluye caderas para evitar pérdida de brazos durante el movimiento
            frontal_required = [11, 12, 13, 14]  # Solo hombros y codos
            threshold = 0.4  # 🆕 BAJADO de 0.5 a 0.4 para mejor tracking
            
            # Requiere que TODOS los 4 puntos estén visibles (ambos brazos completos)
            visible_count = sum(
                1 for i in frontal_required 
                if len(landmarks) > i and landmarks[i].visibility > threshold
            )
            
            if visible_count == 4:  # 4/4 puntos (ambos brazos completos)
                print(f"   ✅ Validación FRONTAL: {visible_count}/4 puntos visibles (threshold={threshold})")
                return True
            else:
                print(f"   ⚠️ Validación FRONTAL FALLIDA: solo {visible_count}/4 puntos visibles (necesita 4/4)")
                return False
        
        else:
            # 🔄 OTROS EJERCICIOS: Requiere TODO (threshold 0.6)
            frontal_required = [11, 12, 13, 14, 23, 24]  # Hombros, codos, caderas
            threshold = 0.6
            frontal_valid = all(
                len(landmarks) > i and landmarks[i].visibility > threshold 
                for i in frontal_required
            )
            if frontal_valid:
                # print(f"   ✅ Validación FRONTAL: Todo visible (threshold={threshold})")  # 🔇 Comentado - performance
                return True
            else:
                # print(f"   ⚠️ Validación FRONTAL FALLIDA")  # 🔇 Comentado - performance
                return False
        
        # 🆕 FALLBACK EXTREMO: Solo cuando hay PÉRDIDA TOTAL de un lado
        
        # Verificar cada lado con umbrales ALTOS
        l_side_points = [11, 13, 23]  # Hombro, codo, cadera izquierda
        r_side_points = [12, 14, 24]  # Hombro, codo, cadera derecha
        
        l_side_excellent = all(
            len(landmarks) > i and landmarks[i].visibility > 0.8 
            for i in l_side_points
        )
        
        r_side_excellent = all(
            len(landmarks) > i and landmarks[i].visibility > 0.8 
            for i in r_side_points
        )
        
        # Verificar PÉRDIDA TOTAL del otro lado
        l_side_lost = any(
            len(landmarks) <= i or landmarks[i].visibility < 0.2 
            for i in l_side_points
        )
        
        r_side_lost = any(
            len(landmarks) <= i or landmarks[i].visibility < 0.2 
            for i in r_side_points
        )
        
        # SOLO permitir unilateral si hay EXCELENCIA de un lado y PÉRDIDA del otro
        if l_side_excellent and r_side_lost:
            return True  # Emergency left
        elif r_side_excellent and l_side_lost:
            return True  # Emergency right
        
        # En TODOS los demás casos, fallar (comportamiento original)
        return False

    # OBSOLETO - Ya no se usa en calculate_joint_angles() simplificado
    # def _detect_true_profile(self, landmarks, w, h):
    #     pass
    
    def detect_side_and_visibility(self, landmarks):
        """
        🆕 DETECCIÓN DE ORIENTACIÓN MEJORADA - Con facing_direction
        
        Detecta qué lado del cuerpo está visible y hacia dónde mira la persona
        También determina si está de PERFIL o FRONTAL
        
        Returns:
            tuple: (tipo_vista, lado, confianza, orientacion, facing_direction)
                - tipo_vista: 'FRONTAL' o 'PERFIL'
                - lado: 'left', 'right' o None (si frontal) [ID de landmark]
                - confianza: float (0.0 a 1.0)
                - orientacion: str descripción legible
                - facing_direction: 'left', 'right', 'front', 'unknown' [dirección real de mirada]
        """
        # 🎯 IMPORT DE MEDIAPIPE (ya debe estar disponible)
        try:
            import mediapipe as mp
            mp_pose = mp.solutions.pose
        except ImportError:
            print("⚠️ MediaPipe no disponible")
            return 'PERFIL', 'right', 0.5, 'detectando...', 'unknown'  # 🆕 Incluir facing_direction
        
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
        # Umbral: si la distancia entre hombros > 0.12 (normalizado) = probablemente frontal
        
        avg_shoulder_visibility = (left_visibility + right_visibility) / 2
        
        # 🆕 LOG DE DEBUG PARA ABDUCCIÓN (comentar después de probar)
        print(f"🔍 DETECCIÓN FRONTAL DEBUG:")
        print(f"   shoulder_distance: {shoulder_distance:.3f} (requiere > 0.15)")
        print(f"   avg_visibility: {avg_shoulder_visibility:.3f} (requiere > 0.6)")
        print(f"   left_vis: {left_visibility:.3f}, right_vis: {right_visibility:.3f}")
        print(f"   Ejercicio actual: {self.current_exercise}")
        print(f"   Camera orientation requerida: {self.current_camera_orientation}")
        
        # 🆕 UMBRALES MÁS ESTRICTOS PARA FRONTAL (evitar falsos positivos de perfil)
        # Requiere: distancia > 0.15 (MÁS ESTRICTO), visibilidad > 0.6 (MÁS ESTRICTO)
        # Esto evita que un perfil con ambos hombros visibles se detecte como frontal
        if shoulder_distance > 0.15 and avg_shoulder_visibility > 0.6 and left_visibility > 0.6 and right_visibility > 0.6:
            print(f"   ✅ DETECTADO: FRONTAL (distancia={shoulder_distance:.3f}, vis={avg_shoulder_visibility:.3f})")
            # Vista FRONTAL (requiere ambos hombros bien visibles y separados)
            view_type = "FRONTAL"
            side = None  # No aplica en vista frontal
            confidence = avg_shoulder_visibility
            orientation = "de frente"
            facing_direction = 'front'  # 🆕 En vista frontal, siempre es 'front'
        else:
            print(f"   ✅ DETECTADO: SAGITAL/PERFIL (distancia={shoulder_distance:.3f}, vis={avg_shoulder_visibility:.3f})")
            # Vista de PERFIL (SAGITAL en nomenclatura biomecánica)
            view_type = "SAGITAL"  # ✅ CORREGIDO: Usar "SAGITAL" en lugar de "PERFIL"
            
            # Determinar orientación basado en la posición de la nariz respecto a los hombros
            nose_x = nose.x
            left_shoulder_x = left_shoulder.x
            right_shoulder_x = right_shoulder.x
            
            shoulder_center_x = (left_shoulder_x + right_shoulder_x) / 2
            
            # 🆕 CALCULAR facing_direction basado en posición de la nariz (MÁS ROBUSTO)
            # Threshold: 0.05 (5% del ancho del frame normalizado)
            if nose_x < shoulder_center_x - 0.05:
                facing_direction = 'left'  # Nariz a la izquierda = mirando hacia la izquierda
            elif nose_x > shoulder_center_x + 0.05:
                facing_direction = 'right'  # Nariz a la derecha = mirando hacia la derecha
            else:
                facing_direction = 'unknown'  # En zona ambigua
            
            # Calcular qué hombro está más de perfil (más visible y más alejado de la nariz)
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
        
        # 🆕 RETORNAR 5 VALORES (backward compatible)
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
            - Ejercicio SAGITAL (flexión) → requiere facing='left' o 'right'
        """
        try:
            # 🔍 DETECTAR orientación actual
            view_type, side, confidence, orientation, facing_direction = self.detect_side_and_visibility(landmarks)
            
            # 🎯 NORMALIZAR valores para comparación
            required_orientation = self.current_camera_orientation.lower()  # 'frontal' o 'sagital'
            detected_facing = facing_direction.lower()  # 'front', 'left', 'right', 'unknown'
            
            print(f"🧭 [validate_orientation_by_facing]")
            print(f"   Requerida: {required_orientation}")
            print(f"   Detectada: {detected_facing} (view_type={view_type})")
            
            # 🎯 VALIDACIÓN SEGÚN TIPO DE EJERCICIO
            if required_orientation == 'frontal':
                # ✅ Ejercicio FRONTAL: necesita mirar de frente
                is_valid = (detected_facing == 'front')
                print(f"   → Ejercicio FRONTAL: {'✅ VÁLIDO' if is_valid else '❌ INVÁLIDO'} (facing={detected_facing})")
                return is_valid
                
            elif required_orientation == 'sagital':
                # ✅ Ejercicio SAGITAL: necesita mirar left o right (perfil)
                is_valid = (detected_facing in ['left', 'right'])
                print(f"   → Ejercicio SAGITAL: {'✅ VÁLIDO' if is_valid else '❌ INVÁLIDO'} (facing={detected_facing})")
                return is_valid
                
            else:
                # ⚠️ Orientación desconocida - aceptar por defecto
                print(f"   ⚠️ Orientación requerida desconocida: {required_orientation}")
                return True
                
        except Exception as e:
            print(f"❌ Error validando orientación: {e}")
            return False  # 🚨 Fallar seguro en caso de error

    def calculate_joint_angles(self, landmarks, frame_dimensions):
        """
        ✅ CÁLCULO SIMPLIFICADO - SOLO método correcto de test_shoulder_extension.py
        🎯 SIEMPRE usa calculate_shoulder_angle_new_system() - bilateral
        """
        h, w = frame_dimensions
        
        try:
            # 🧭 DETECCIÓN DE ORIENTACIÓN (solo informativa para overlay)
            orientation_info = self.orientation_detector.detect_orientation_adaptive(landmarks)
            
            # ✅ USAR SIEMPRE MÉTODO CORRECTO: _calculate_bilateral_with_fixed_references
            # Este método usa internamente calculate_shoulder_angle_new_system() que es
            # IDÉNTICO al método de test_shoulder_extension.py
            angles = self._calculate_bilateral_with_fixed_references(
                landmarks, w, h, orientation_info, self.current_exercise
            )
            
            return angles
                
        except Exception as e:
            print(f"❌ Error en cálculo de hombro: {e}")
            return self._error_shoulder_data()

    # ❌ MÉTODO OBSOLETO - Comentado: Ya no se usa, ahora siempre bilateral
    # def _calculate_unilateral_profile_scientific(self, landmarks, w, h, orientation_info, exercise_type, side):
    #     """OBSOLETO - Usaba FixedSpatialReferences (incorrecto)"""
    #     pass

    # ❌ MÉTODO OBSOLETO - Comentado: Reemplazado por _calculate_bilateral_with_fixed_references
    # def _calculate_bilateral_shoulder_angles_original(self, landmarks, w, h, orientation_info):
    #     """OBSOLETO - Usaba calculate_angle_biomechanical (3 puntos, sin dirección)"""
    #     pass

    def _calculate_bilateral_with_fixed_references(self, landmarks, w, h, orientation_info, exercise_type):
        """
        🆕 MÉTODO CORRECTO - ADAPTADO DE test_shoulder_extension.py
        
        USA: calculate_shoulder_angle_new_system() que es IDÉNTICO a
             calculate_extension_angle() de test_shoulder_extension.py
        
        Cálculo: hombro→codo vs hombro→cadera (NO hombro→muñeca vs vertical)
        Sistema: 0° = brazo abajo, +/- según dirección
        """
        
        # =============================================================================
        # LADO DERECHO - EXACTO DE test_shoulder_extension.py
        # =============================================================================
        shoulder_r = landmarks[12]
        elbow_r = landmarks[14]
        hip_r = landmarks[24]
        wrist_r = landmarks[16]  # Para visualización
        
        # Convertir a coordenadas pixel
        shoulder_r_pos = [shoulder_r.x * w, shoulder_r.y * h]
        elbow_r_pos = [elbow_r.x * w, elbow_r.y * h]
        hip_r_pos = [hip_r.x * w, hip_r.y * h]
        
        # 🆕 USAR SISTEMA DE test_shoulder_extension.py
        angle_r = self.calculate_shoulder_angle_new_system(
            shoulder_r_pos, hip_r_pos, elbow_r_pos, 'right'
        )
        
        # =============================================================================
        # LADO IZQUIERDO - EXACTO DE test_shoulder_extension.py
        # =============================================================================
        shoulder_l = landmarks[11]
        elbow_l = landmarks[13]
        hip_l = landmarks[23]
        wrist_l = landmarks[15]  # Para visualización
        
        # Convertir a coordenadas pixel
        shoulder_l_pos = [shoulder_l.x * w, shoulder_l.y * h]
        elbow_l_pos = [elbow_l.x * w, elbow_l.y * h]
        hip_l_pos = [hip_l.x * w, hip_l.y * h]
        
        # 🆕 USAR SISTEMA DE test_shoulder_extension.py
        angle_l = self.calculate_shoulder_angle_new_system(
            shoulder_l_pos, hip_l_pos, elbow_l_pos, 'left'
        )
        
        # =============================================================================
        # SEPARACIÓN (mantener cálculo original)
        # =============================================================================
        shoulder_separation = self.calculate_angle_biomechanical(
            shoulder_l_pos,
            [(shoulder_l_pos[0] + shoulder_r_pos[0])/2, (shoulder_l_pos[1] + shoulder_r_pos[1])/2],
            shoulder_r_pos
        )
        
        # =============================================================================
        # FILTROS (igual que original)
        # =============================================================================
        filtered_flexion_r = self.apply_temporal_filter(angle_r, 'right_shoulder_flexion')
        filtered_flexion_l = self.apply_temporal_filter(angle_l, 'left_shoulder_flexion')
        filtered_separation = self.apply_temporal_filter(shoulder_separation, 'shoulder_separation')
        
        # =============================================================================
        # RETURN (estructura compatible con visualización)
        # 🪞 CORRECCIÓN ESPEJO: MediaPipe está en espejo, entonces:
        #    - landmark[12] 'right' = TU brazo IZQUIERDO → guardar como 'left'
        #    - landmark[11] 'left' = TU brazo DERECHO → guardar como 'right'
        # =============================================================================
        return {
            'analysis_mode': 'BILATERAL_FIXED_REF',
            'right_shoulder_flexion': filtered_flexion_l,  # 🪞 INTERCAMBIADO
            'left_shoulder_flexion': filtered_flexion_r,   # 🪞 INTERCAMBIADO
            'shoulder_separation': filtered_separation,
            'raw_right_flexion': angle_l,  # 🪞 INTERCAMBIADO
            'raw_left_flexion': angle_r,   # 🪞 INTERCAMBIADO
            'raw_separation': shoulder_separation,
            'positions': {
                'shoulder_r': shoulder_l_pos,  # 🪞 INTERCAMBIADO
                'elbow_r': elbow_l_pos,        # 🪞 INTERCAMBIADO
                'wrist_r': [wrist_l.x * w, wrist_l.y * h] if wrist_l.visibility > 0.3 else [0, 0],  # 🪞 INTERCAMBIADO
                'hip_r': hip_l_pos,            # 🪞 INTERCAMBIADO
                'shoulder_l': shoulder_r_pos,  # 🪞 INTERCAMBIADO
                'elbow_l': elbow_r_pos,        # 🪞 INTERCAMBIADO
                'wrist_l': [wrist_r.x * w, wrist_r.y * h] if wrist_r.visibility > 0.3 else [0, 0],  # 🪞 INTERCAMBIADO
                'hip_l': hip_r_pos             # 🪞 INTERCAMBIADO
            },
            'fallback': {
                'use_elbow_r': False,  # Siempre usamos codo en el cálculo
                'use_elbow_l': False   # Siempre usamos codo en el cálculo
            },
            'orientation_info': orientation_info
        }

    # OBSOLETO - Ya no se usa en calculate_joint_angles() simplificado
    # def _emergency_unilateral_analysis(self, landmarks, w, h, orientation_info):
    #     pass

    def draw_joint_visualization(self, frame, landmarks, angles):
        """
        ✅ VISUALIZACIÓN SIMPLIFICADA - SOLO método correcto de test
        Usa SIEMPRE _draw_bilateral_visualization_fixed_axes (vectores verdes/azules)
        """
        h, w, _ = frame.shape
        
        try:
            # ✅ USAR SIEMPRE VISUALIZACIÓN CORRECTA (test_shoulder_extension.py style)
            return self._draw_bilateral_visualization_fixed_axes(frame, landmarks, angles, w, h)
                
        except Exception as e:
            print(f"❌ Error en visualización: {e}")
            return frame

    # ❌ MÉTODO OBSOLETO - Comentado: Ya no se usa
    # def _draw_unilateral_profile_visualization(self, frame, landmarks, angles, w, h):
    #     """OBSOLETO - Visualización unilateral ya no se usa"""
    #     pass

    def _draw_arc_between_vectors(self, frame, origin, vec_movil, vec_fixed, angle, radius=40, color=(0, 255, 0), thickness=3):
        """
        🆕 HELPER: Dibuja arco entre vector móvil (brazo) y vector fijo (vertical)
        
        Args:
            frame: Frame de video
            origin: Punto de origen (hombro) (x, y)
            vec_movil: Vector del segmento móvil {x, y} (brazo: muñeca - hombro)
            vec_fixed: Vector de referencia fija {x, y} (típicamente vertical: {0, -1})
            angle: Ángulo calculado en grados
            radius: Radio del arco
            color: Color BGR del arco
            thickness: Grosor del arco
        
        Returns:
            frame modificado
        """
        try:
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
            # cv2.ellipse necesita: centro, ejes, ángulo_rotación, start_angle, end_angle, color, grosor
            cv2.ellipse(
                frame, 
                tuple(map(int, origin)),  # Centro del arco (hombro)
                (radius, radius),          # Ejes del arco (circular)
                0,                         # Rotación (0 = sin rotar)
                angle_fixed_deg,           # Ángulo inicial (referencia fija)
                angle_movil_deg,           # Ángulo final (vector brazo)
                color,                     # Color
                thickness                  # Grosor
            )
            
            return frame
            
        except Exception as e:
            # 🛡️ Silencioso: No romper visualización si arco falla
            print(f"⚠️ Error dibujando arco científico: {e}")
            return frame

    def _draw_bilateral_visualization_fixed_axes(self, frame, landmarks, angles, w, h):
        """
        🆕 VISUALIZACIÓN CIENTÍFICA - ADAPTADA DE test_shoulder_extension.py
        
        Características de test_shoulder_extension.py:
        - Puntos grandes (8px) en colores específicos
        - Líneas verdes (2px) para referencia vertical (cadera→hombro)
        - Líneas azules (2px) para brazo (hombro→codo→muñeca)
        - Arcos científicos entre brazo y vertical
        - Sin puntos faciales
        
        🆕 MEJORAS VISUALES:
        - Solo muestra el lado activo (según orientación detectada)
        - Símbolo de grado como círculo pequeño arriba del número
        - Visualización más limpia y menos confusa
        """
        
        pos = angles.get('positions', {})
        fallback = angles.get('fallback', {})
        required_keys = ['shoulder_r', 'shoulder_l', 'hip_r', 'hip_l', 'elbow_r', 'elbow_l']
        
        if not (pos and all(k in pos for k in required_keys)):
            return frame
        
        # 🆕 DETECTAR QUÉ LADO MOSTRAR - Ahora con facing_direction
        view_type, detected_side, confidence, orientation, facing_direction = self.detect_side_and_visibility(landmarks)
        
        # 🎯 DETERMINAR LADOS A MOSTRAR:
        # - FRONTAL (abducción): Mostrar AMBOS lados
        # - SAGITAL (flexión/extensión): Mostrar SOLO el lado detectado
        # 🪞 NOTA: detected_side es landmark ID, pero pos[] ya está intercambiado
        #          detected_side='left' → pos['shoulder_r'] tiene datos del brazo derecho usuario
        show_right = False
        show_left = False
        
        if view_type == 'FRONTAL':
            # Abducción: Mostrar ambos lados
            show_right = True
            show_left = True
        elif view_type == 'SAGITAL':  # ✅ CORREGIDO: Usar "SAGITAL" en lugar de "PERFIL"
            # Flexión/Extensión: Solo el lado detectado
            # 🪞 detected_side='left' (landmark 11) → Usuario muestra brazo derecho → show_right
            # 🪞 detected_side='right' (landmark 12) → Usuario muestra brazo izquierdo → show_left
            if detected_side == 'left':
                show_right = True  # Brazo derecho del usuario
                show_left = False
            elif detected_side == 'right':
                show_right = False
                show_left = True   # Brazo izquierdo del usuario
            else:
                # Si no se detectó lado específico, mostrar ambos (fallback)
                show_right = True
                show_left = True
        
        # =============================================================================
        # 🎨 DIBUJAR VECTORES Y PUNTOS - ESTILO test_shoulder_extension.py
        # =============================================================================
        
        # � CONVERTIR A COORDENADAS INT
        shoulder_r = (int(pos['shoulder_r'][0]), int(pos['shoulder_r'][1]))
        elbow_r = (int(pos['elbow_r'][0]), int(pos['elbow_r'][1]))
        hip_r = (int(pos['hip_r'][0]), int(pos['hip_r'][1]))
        
        shoulder_l = (int(pos['shoulder_l'][0]), int(pos['shoulder_l'][1]))
        elbow_l = (int(pos['elbow_l'][0]), int(pos['elbow_l'][1]))
        hip_l = (int(pos['hip_l'][0]), int(pos['hip_l'][1]))
        
        # 🆕 OBTENER MUÑECAS SI EXISTEN
        wrist_r = None
        wrist_l = None
        if pos.get('wrist_r') and pos['wrist_r'] != [0, 0]:
            wrist_r = (int(pos['wrist_r'][0]), int(pos['wrist_r'][1]))
        if pos.get('wrist_l') and pos['wrist_l'] != [0, 0]:
            wrist_l = (int(pos['wrist_l'][0]), int(pos['wrist_l'][1]))
        
        # ✅ BRAZO DERECHO - Solo si está activo
        if show_right:
            # Puntos clave
            cv2.circle(frame, shoulder_r, 8, (0, 255, 255), -1)  # Amarillo - Hombro
            cv2.circle(frame, hip_r, 8, (255, 0, 255), -1)       # Magenta - Cadera
            cv2.circle(frame, elbow_r, 8, (255, 255, 0), -1)     # Cyan - Codo
            
            # Líneas de referencia
            cv2.line(frame, hip_r, shoulder_r, (0, 255, 0), 2)       # Verde - Línea vertical referencia
            cv2.line(frame, shoulder_r, elbow_r, (255, 0, 0), 2)     # Azul - Brazo
            if wrist_r:
                cv2.line(frame, elbow_r, wrist_r, (255, 0, 0), 2)    # Azul - Antebrazo
        
        # ✅ BRAZO IZQUIERDO - Solo si está activo
        if show_left:
            # Puntos clave
            cv2.circle(frame, shoulder_l, 8, (0, 255, 255), -1)  # Amarillo - Hombro
            cv2.circle(frame, hip_l, 8, (255, 0, 255), -1)       # Magenta - Cadera
            cv2.circle(frame, elbow_l, 8, (255, 255, 0), -1)     # Cyan - Codo
            
            # Líneas de referencia
            cv2.line(frame, hip_l, shoulder_l, (0, 255, 0), 2)       # Verde - Línea vertical referencia
            cv2.line(frame, shoulder_l, elbow_l, (255, 0, 0), 2)     # Azul - Brazo
            if wrist_l:
                cv2.line(frame, elbow_l, wrist_l, (255, 0, 0), 2)    # Azul - Antebrazo
        
        # ✅ LÍNEA DE CONEXIÓN ENTRE CADERAS (siempre visible para estabilidad visual)
        cv2.line(frame, hip_l, hip_r, (0, 255, 0), 2)            # Verde - Línea base
        
        # =============================================================================
        # 🆕 ARCOS CIENTÍFICOS - Solo lado activo
        # =============================================================================
        
        # LADO DERECHO - Solo si está activo
        if show_right:
            endpoint_r = wrist_r if wrist_r else elbow_r
            if endpoint_r:
                vec_brazo_r = {
                    'x': endpoint_r[0] - shoulder_r[0],
                    'y': endpoint_r[1] - shoulder_r[1]
                }
                vec_vertical = {'x': 0, 'y': 1}  # Vertical hacia ABAJO
                
                frame = self._draw_arc_between_vectors(
                    frame, 
                    pos['shoulder_r'], 
                    vec_brazo_r, 
                    vec_vertical, 
                    angles['right_shoulder_flexion'], 
                    radius=60,
                    color=(0, 100, 200),  # Naranja suave
                    thickness=3
                )
        
        # LADO IZQUIERDO - Solo si está activo
        if show_left:
            endpoint_l = wrist_l if wrist_l else elbow_l
            if endpoint_l:
                vec_brazo_l = {
                    'x': endpoint_l[0] - shoulder_l[0],
                    'y': endpoint_l[1] - shoulder_l[1]
                }
                vec_vertical = {'x': 0, 'y': 1}  # Vertical hacia ABAJO
                
                frame = self._draw_arc_between_vectors(
                    frame, 
                    pos['shoulder_l'], 
                    vec_brazo_l, 
                    vec_vertical, 
                    angles['left_shoulder_flexion'], 
                    radius=60,
                    color=(100, 200, 0),  # Verde lima suave
                thickness=3
            )
        
        # =============================================================================
        # 📐 MOSTRAR ÁNGULOS - Solo lado activo + Círculo como símbolo de grado
        # =============================================================================
        
        # 🎯 ÁNGULO DERECHO - Solo si está activo
        if show_right:
            angle_value_r = angles['right_shoulder_flexion']
            angle_text_r = f"{abs(angle_value_r):.1f}"  # Usar abs() para mostrar positivo
            
            # Calcular posición del texto
            text_x_r = shoulder_r[0] - 40
            text_y_r = shoulder_r[1] - 20
            
            # Dibujar el número del ángulo
            cv2.putText(frame, angle_text_r, 
                       (text_x_r, text_y_r),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
            
            # 🆕 Calcular ancho del texto para posicionar el símbolo de grado
            (text_width, text_height), _ = cv2.getTextSize(angle_text_r, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
            
            # 🆕 Dibujar "o" pequeño como símbolo de grado (arriba a la derecha del número)
            degree_x = text_x_r + text_width + 2  # 2px a la derecha del texto
            degree_y = text_y_r - int(text_height * 0.6)  # Arriba, alineado con el top del número
            cv2.putText(frame, "o", (degree_x, degree_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)  # "o" pequeño amarillo
        
        # 🎯 ÁNGULO IZQUIERDO - Solo si está activo
        if show_left:
            angle_value_l = angles['left_shoulder_flexion']
            angle_text_l = f"{abs(angle_value_l):.1f}"  # Usar abs() para mostrar positivo
            
            # Calcular posición del texto
            text_x_l = shoulder_l[0] + 20
            text_y_l = shoulder_l[1] - 20
            
            # Dibujar el número del ángulo
            cv2.putText(frame, angle_text_l, 
                       (text_x_l, text_y_l),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
            
            # 🆕 Calcular ancho del texto para posicionar el símbolo de grado
            (text_width, text_height), _ = cv2.getTextSize(angle_text_l, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
            
            # 🆕 Dibujar "o" pequeño como símbolo de grado (arriba a la derecha del número)
            degree_x = text_x_l + text_width + 2  # 2px a la derecha del texto
            degree_y = text_y_l - int(text_height * 0.6)  # Arriba, alineado con el top del número
            cv2.putText(frame, "o", (degree_x, degree_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)  # "o" pequeño amarillo
        
        # Info de orientación
        self._draw_orientation_info(frame, angles.get('orientation_info', {}))
        
        return frame

    # OBSOLETO - Ya no se usa, ahora usamos _draw_bilateral_visualization_fixed_axes()
    # def _draw_bilateral_visualization_original(self, frame, landmarks, angles, w, h):
    #     pass

    def _draw_emergency_visualization(self, frame, landmarks, angles, w, h):
        """🚨 Visualización para casos de emergencia"""
        
        pos = angles.get('positions', {})
        analysis_mode = angles.get('analysis_mode', '')
        
        if 'LEFT' in analysis_mode and pos.get('shoulder_l'):
            # Solo lado izquierdo
            shoulder_connections = [(11, 13), (11, 23)]
            
            for connection in shoulder_connections:
                if len(landmarks) > max(connection):
                    start_point = landmarks[connection[0]]
                    end_point = landmarks[connection[1]]
                    
                    start_x, start_y = int(start_point.x * w), int(start_point.y * h)
                    end_x, end_y = int(end_point.x * w), int(end_point.y * h)
                    
                    cv2.line(frame, (start_x, start_y), (end_x, end_y), (255, 165, 0), 3)
            
            if pos.get('elbow_l') and pos.get('hip_l'):
                frame = self.draw_angle_arc_advanced(
                    frame, pos['shoulder_l'], pos['elbow_l'], pos['hip_l'], 
                    angles.get('left_shoulder_flexion', 0), 30, (255, 100, 0)
                )
            
            cv2.circle(frame, (int(pos['shoulder_l'][0]), int(pos['shoulder_l'][1])), 10, (128, 0, 255), -1)
            
            # 📊 TEXTO CIENTÍFICO (comentado - redundante con audio)
            # frame = self.add_text_with_pillow(frame, 
            #     f"🚨 SAGITAL - HOMBRO IZQ: {angles.get('left_shoulder_flexion', 0):.0f}°",
            #     (10, 40), font_size=16, color=(255, 200, 0))
            
            # cv2.putText(frame, "Modo Emergencia - Lado derecho no visible", 
                       #(10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 100), 1)
            
        elif 'RIGHT' in analysis_mode and pos.get('shoulder_r'):
            # Solo lado derecho
            shoulder_connections = [(12, 14), (12, 24)]
            
            for connection in shoulder_connections:
                if len(landmarks) > max(connection):
                    start_point = landmarks[connection[0]]
                    end_point = landmarks[connection[1]]
                    
                    start_x, start_y = int(start_point.x * w), int(start_point.y * h)
                    end_x, end_y = int(end_point.x * w), int(end_point.y * h)
                    
                    cv2.line(frame, (start_x, start_y), (end_x, end_y), (255, 165, 0), 3)
            
            if pos.get('elbow_r') and pos.get('hip_r'):
                frame = self.draw_angle_arc_advanced(
                    frame, pos['shoulder_r'], pos['elbow_r'], pos['hip_r'], 
                    angles.get('right_shoulder_flexion', 0), 30, (255, 100, 0)
                )
            
            cv2.circle(frame, (int(pos['shoulder_r'][0]), int(pos['shoulder_r'][1])), 10, (255, 0, 128), -1)
            
            # 📊 TEXTO CIENTÍFICO (comentado - redundante con audio)
            # frame = self.add_text_with_pillow(frame, 
            #     f"🚨 SAGITAL - HOMBRO DER: {angles.get('right_shoulder_flexion', 0):.0f}°",
            #     (10, 40), font_size=16, color=(255, 200, 0))
            
            # cv2.putText(frame, "Modo Emergencia - Lado izquierdo no visible", 
                       #(10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 100), 1)
        
        self._draw_orientation_info(frame, angles.get('orientation_info', {}))
        return frame

    def _draw_orientation_info(self, frame, orientation_info):
        """🧭 Info de orientación - esquina superior derecha"""
        if not orientation_info or orientation_info.get('orientation') in ['ERROR', 'INSUFFICIENT_DATA']:
            return
        
        h, w, _ = frame.shape
        info_x = w - 280
        info_y = 30
        
        orientation = orientation_info.get('orientation', 'UNKNOWN')
        confidence = orientation_info.get('confidence', 0.0)
        
        # cv2.putText(frame, f"Plano: {orientation}", 
        #           (info_x, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # cv2.putText(frame, f"Conf: {confidence:.0%}", 
        #           (info_x, info_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        # Indicador de calidad (comentado - limpieza visual)
        # color = (0, 255, 0) if confidence > 0.8 else (0, 255, 255) if confidence > 0.6 else (0, 0, 255)
        # cv2.circle(frame, (info_x - 15, info_y + 5), 6, color, -1)

    def _insufficient_shoulder_data(self, orientation_info):
        return {
            'analysis_mode': 'INSUFFICIENT',
            'right_shoulder_flexion': 0, 'left_shoulder_flexion': 0,
            'shoulder_separation': 0,
            'raw_right_flexion': 0, 'raw_left_flexion': 0, 'raw_separation': 0,
            'positions': {},
            'orientation_info': orientation_info
        }
    
    def _error_shoulder_data(self):
        return {
            'analysis_mode': 'ERROR',
            'right_shoulder_flexion': 0, 'left_shoulder_flexion': 0,
            'shoulder_separation': 0,
            'raw_right_flexion': 0, 'raw_left_flexion': 0, 'raw_separation': 0,
            'positions': {},
            'orientation_info': {'orientation': 'ERROR', 'confidence': 0.0}
        }
    
    # =============================================================================
    # 🆕 NUEVOS MÉTODOS DE CÁLCULO - SISTEMA CORRECTO (test_shoulder_extension.py)
    # =============================================================================
    
    def calculate_shoulder_angle_new_system(self, shoulder, hip, elbow, side):
        """
        🆕 SISTEMA GONIÓMETRO CON DIRECCIÓN
        
        Backend mantiene signos para distinguir movimientos:
        - 0° = Posición neutra (brazo apuntando ABAJO)
        - Positivo (+) = Flexión/Abducción (hacia adelante/arriba/lateral)
        - Negativo (-) = Extensión (hacia atrás)
        
        Frontend usa abs() para mostrar siempre positivo
        ROM tracking usa abs() para capturar máximo alcanzado
        
        Args:
            shoulder: [x, y] coordenadas del hombro
            hip: [x, y] coordenadas de la cadera
            elbow: [x, y] coordenadas del codo
            side: 'left' o 'right' - lado del cuerpo
        
        Returns:
            float: ángulo en grados con signo (-180 a +180)
                  - Positivo: Flexión/Abducción
                  - Negativo: Extensión
        """
        # Vector vertical hacia abajo (de hombro a cadera) - Referencia de 0°
        down_vector = np.array([hip[0] - shoulder[0], hip[1] - shoulder[1]])
        
        # Vector del brazo (de hombro a codo)
        arm_vector = np.array([elbow[0] - shoulder[0], elbow[1] - shoulder[1]])
        
        # Normalizar vectores
        down_norm = np.linalg.norm(down_vector)
        arm_norm = np.linalg.norm(arm_vector)
        
        if down_norm == 0 or arm_norm == 0:
            return 0
        
        down_vector_normalized = down_vector / down_norm
        arm_vector_normalized = arm_vector / arm_norm
        
        # Calcular ángulo entre el vector hacia abajo y el brazo
        dot_product = np.dot(down_vector_normalized, arm_vector_normalized)
        dot_product = np.clip(dot_product, -1.0, 1.0)
        
        # Ángulo sin signo (0° a 180°)
        angle_magnitude = np.degrees(np.arccos(dot_product))
        
        # 🎯 CALCULAR DIRECCIÓN con producto cruz
        # En 2D: cross = x1*y2 - y1*x2
        cross_product = down_vector[0] * arm_vector[1] - down_vector[1] * arm_vector[0]
        
        # Determinar el signo según el lado y la dirección
        # Para hombro izquierdo:
        #   - Si cross > 0 → brazo hacia la izquierda (hacia donde mira) = POSITIVO
        #   - Si cross < 0 → brazo hacia la derecha (atrás) = NEGATIVO
        # Para hombro derecho:
        #   - Si cross < 0 → brazo hacia la derecha (hacia donde mira) = POSITIVO
        #   - Si cross > 0 → brazo hacia la izquierda (atrás) = NEGATIVO
        
        if side == 'left':
            if cross_product > 0:
                # Brazo hacia la izquierda (adelante) = POSITIVO
                angle = angle_magnitude
            else:
                # Brazo hacia la derecha (atrás) = NEGATIVO
                angle = -angle_magnitude
        else:  # side == 'right'
            if cross_product < 0:
                # Brazo hacia la derecha (adelante) = POSITIVO
                angle = angle_magnitude
            else:
                # Brazo hacia la izquierda (atrás) = NEGATIVO
                angle = -angle_magnitude
        
        return angle  # ✅ Retorna con signo: positivo=flexión, negativo=extensión
    
    def calculate_abduction_angle_new_system(self, shoulder, hip, elbow):
        """
        🆕 CÁLCULO DE ABDUCCIÓN CON SISTEMA CORRECTO
        Basado en test_shoulder_extension.py
        
        - 0° = Brazo pegado al cuerpo (paralelo a la línea hombro-cadera)
        - 90° = Brazo horizontal (perpendicular al cuerpo)
        - 180° = Brazo completamente levantado sobre la cabeza
        
        Args:
            shoulder: [x, y] coordenadas del hombro
            hip: [x, y] coordenadas de la cadera
            elbow: [x, y] coordenadas del codo
        
        Returns:
            float: ángulo de abducción en grados (0 a 180)
        """
        # Vector vertical hacia abajo (de hombro a cadera) - Referencia de 0°
        down_vector = np.array([hip[0] - shoulder[0], hip[1] - shoulder[1]])
        
        # Vector del brazo (de hombro a codo)
        arm_vector = np.array([elbow[0] - shoulder[0], elbow[1] - shoulder[1]])
        
        # Normalizar vectores
        down_norm = np.linalg.norm(down_vector)
        arm_norm = np.linalg.norm(arm_vector)
        
        if down_norm == 0 or arm_norm == 0:
            return 0
        
        down_vector_normalized = down_vector / down_norm
        arm_vector_normalized = arm_vector / arm_norm
        
        # Calcular ángulo entre el vector hacia abajo y el brazo
        dot_product = np.dot(down_vector_normalized, arm_vector_normalized)
        dot_product = np.clip(dot_product, -1.0, 1.0)
        
        # Ángulo de abducción (siempre positivo en vista frontal)
        angle = np.degrees(np.arccos(dot_product))
        
        return angle
    
    ################################################
    def calculate_with_fixed_reference(self, landmarks, orientation, exercise_type):
        """📐 CÁLCULO CON REFERENCIA FIJA - MÁS PRECISO"""
        
        from core.fixed_references import FixedSpatialReferences
        ref_system = FixedSpatialReferences()
        
        # Obtener puntos del segmento móvil
        shoulder = landmarks[11] if landmarks[11].visibility > 0.7 else landmarks[12]
        wrist = landmarks[15] if landmarks[15].visibility > 0.7 else landmarks[16]
        
        # Vector del segmento (hombro-muñeca)
        segment_vector = {
            "x": wrist.x - shoulder.x,
            "y": wrist.y - shoulder.y
        }
        
        # 📐 ÁNGULO CON REFERENCIA FIJA
        angle = ref_system.calculate_angle_with_fixed_reference(
            segment_vector, orientation, exercise_type
        )
        
        # ✅ VALIDAR CALIDAD
        quality = ref_system.validate_measurement_quality(
            angle, segment_vector, orientation, exercise_type
        )
        
        return {
            "angle": angle,
            "quality": quality,
            "reference_type": "FIXED_SPATIAL",
            "segment_vector": segment_vector,
            "exercise_type": exercise_type
        }

    # OBSOLETO - Ya no se usa, ahora usamos calculate_joint_angles() simplificado
    # def calculate_joint_angles_for_exercise(self, landmarks, frame_dimensions, exercise_type):
    #     pass
    
    # OBSOLETO - Ya no se usa, ahora usamos calculate_joint_angles() simplificado
    # def _calculate_flexion_sagital(self, landmarks, frame_dimensions):
    #     pass
    
    # OBSOLETO - Ya no se usa, ahora usamos calculate_joint_angles() simplificado
    # def _calculate_abduction_frontal(self, landmarks, frame_dimensions):
    #     pass
    
    # OBSOLETO - Ya no se usa, ahora usamos calculate_joint_angles() simplificado  
    # def _calculate_rotation_transversal(self, landmarks, frame_dimensions):
    #     pass
    
    def _calculate_abduction_frontal(self, landmarks, frame_dimensions):
        """
        🆕 CÁLCULO DE ABDUCCIÓN CON SISTEMA CORRECTO
        Adaptado de test_shoulder_extension.py
        
        - 0° = Brazo pegado al cuerpo
        - 90° = Brazo horizontal
        - 180° = Brazo sobre la cabeza
        """
        h, w = frame_dimensions
        
        try:
            # ✅ ABDUCCIÓN DERECHA (elevación lateral)
            shoulder_r = [landmarks[12].x * w, landmarks[12].y * h]
            elbow_r = [landmarks[14].x * w, landmarks[14].y * h]
            hip_r = [landmarks[24].x * w, landmarks[24].y * h]
            
            # 🆕 USAR NUEVO SISTEMA DE CÁLCULO DE ABDUCCIÓN
            abduction_angle_r = self.calculate_abduction_angle_new_system(
                shoulder_r, hip_r, elbow_r
            )
            
            # ✅ ABDUCCIÓN IZQUIERDA
            shoulder_l = [landmarks[11].x * w, landmarks[11].y * h]
            elbow_l = [landmarks[13].x * w, landmarks[13].y * h]
            hip_l = [landmarks[23].x * w, landmarks[23].y * h]
            
            # 🆕 USAR NUEVO SISTEMA DE CÁLCULO DE ABDUCCIÓN
            abduction_angle_l = self.calculate_abduction_angle_new_system(
                shoulder_l, hip_l, elbow_l
            )
            
            # ✅ Ajustar ángulos (0° = brazo colgando, 180° = brazo arriba)
            abduction_angle_r = max(0, min(180, abduction_angle_r))
            abduction_angle_l = max(0, min(180, abduction_angle_l))
            
            return {
                'exercise_type': 'abduction',
                'plane': 'frontal',
                'right_shoulder_angle': abduction_angle_r,
                'left_shoulder_angle': abduction_angle_l,
                'right_shoulder_abduction': abduction_angle_r,  # Alias para compatibilidad
                'left_shoulder_abduction': abduction_angle_l,   # Alias para compatibilidad
                'positions': {
                    'shoulder_r': shoulder_r, 'elbow_r': elbow_r, 'hip_r': hip_r,
                    'shoulder_l': shoulder_l, 'elbow_l': elbow_l, 'hip_l': hip_l
                },
                'analysis_quality': 'good' if all([
                    shoulder_r[0] > 0, elbow_r[0] > 0, shoulder_l[0] > 0, elbow_l[0] > 0
                ]) else 'poor',
                'warnings': []
            }
            
        except Exception as e:
            print(f"Error en cálculo de abducción: {e}")
            return self._error_shoulder_data()
    
    def _calculate_rotation_transversal(self, landmarks, frame_dimensions):
        """🆕 NUEVO: Cálculo de rotación transversal"""
        h, w = frame_dimensions
        
        try:
            # ✅ ROTACIÓN DERECHA (codo debe estar flexionado ~90°)
            shoulder_r = [landmarks[12].x * w, landmarks[12].y * h]
            elbow_r = [landmarks[14].x * w, landmarks[14].y * h]
            wrist_r = [landmarks[16].x * w, landmarks[16].y * h]
            
            # Vector del antebrazo (codo a muñeca)
            forearm_vector_r = [wrist_r[0] - elbow_r[0], wrist_r[1] - elbow_r[1]]
            
            # Vector horizontal de referencia (hacia la derecha)
            horizontal_vector = [100, 0]
            
            # Calcular ángulo de rotación
            rotation_angle_r = self.calculate_angle_between_vectors(forearm_vector_r, horizontal_vector)
            
            # ✅ ROTACIÓN IZQUIERDA  
            shoulder_l = [landmarks[11].x * w, landmarks[11].y * h]
            elbow_l = [landmarks[13].x * w, landmarks[13].y * h]
            wrist_l = [landmarks[15].x * w, landmarks[15].y * h]
            
            forearm_vector_l = [wrist_l[0] - elbow_l[0], wrist_l[1] - elbow_l[1]]
            rotation_angle_l = self.calculate_angle_between_vectors(forearm_vector_l, horizontal_vector)
            
            # ✅ Verificar que el codo esté flexionado (calidad del análisis)
            elbow_flexion_r = self.calculate_angle_biomechanical(shoulder_r, elbow_r, wrist_r)
            elbow_flexion_l = self.calculate_angle_biomechanical(shoulder_l, elbow_l, wrist_l)
            
            # ✅ Validar posición (codo debe estar ~90° flexionado)
            quality = 'good'
            warnings = []
            
            if elbow_flexion_r < 70 or elbow_flexion_r > 110:
                quality = 'poor'
                warnings.append('Codo derecho debe estar flexionado ~90°')
                
            if elbow_flexion_l < 70 or elbow_flexion_l > 110:
                quality = 'poor'  
                warnings.append('Codo izquierdo debe estar flexionado ~90°')
            
            # ✅ Ajustar ángulos (0° = antebrazo hacia adelante, 90° = rotación externa máxima)
            rotation_angle_r = max(0, min(90, rotation_angle_r))
            rotation_angle_l = max(0, min(90, rotation_angle_l))
            
            return {
                'exercise_type': 'rotation',
                'plane': 'transversal',
                'right_shoulder_angle': rotation_angle_r,
                'left_shoulder_angle': rotation_angle_l,
                'right_shoulder_rotation': rotation_angle_r,  # Alias para compatibilidad
                'left_shoulder_rotation': rotation_angle_l,   # Alias para compatibilidad
                'positions': {
                    'shoulder_r': shoulder_r, 'elbow_r': elbow_r, 'wrist_r': wrist_r,
                    'shoulder_l': shoulder_l, 'elbow_l': elbow_l, 'wrist_l': wrist_l
                },
                'elbow_angles': {
                    'right_elbow_flexion': elbow_flexion_r,
                    'left_elbow_flexion': elbow_flexion_l
                },
                'analysis_quality': quality,
                'warnings': warnings
            }
            
        except Exception as e:
            print(f"Error en cálculo de rotación: {e}")
            return self._error_shoulder_data()
    
    def calculate_angle_between_vectors(self, vector1, vector2):
        """📐 Calcular ángulo entre dos vectores - MÉTODO HELPER"""
        try:
            # Normalizar vectores
            norm1 = math.sqrt(vector1[0]**2 + vector1[1]**2)
            norm2 = math.sqrt(vector2[0]**2 + vector2[1]**2)
            
            if norm1 == 0 or norm2 == 0:
                return 0
            
            # Producto punto
            dot_product = vector1[0]*vector2[0] + vector1[1]*vector2[1]
            
            # Ángulo en radianes
            cos_angle = dot_product / (norm1 * norm2)
            
            # Clamp para evitar errores numéricos
            cos_angle = max(-1, min(1, cos_angle))
            
            angle_rad = math.acos(cos_angle)
            angle_deg = math.degrees(angle_rad)
            
            return angle_deg
            
        except Exception as e:
            print(f"Error calculando ángulo entre vectores: {e}")
            return 0
    
    def _error_shoulder_data(self):
        """❌ Datos de error estándar"""
        return {
            'exercise_type': self.current_exercise,
            'plane': 'unknown',
            'right_shoulder_angle': 0,
            'left_shoulder_angle': 0,
            'analysis_quality': 'error',
            'warnings': ['Error en análisis'],
            'positions': {}
        }