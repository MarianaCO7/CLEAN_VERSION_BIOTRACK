"""
🦴 ANALIZADOR DE CUELLO COMPLETO
🎯 Heredando toda la funcionalidad base + específico de cuello
"""

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import numpy as np
import cv2
import math
from core.base_analyzer import BaseJointAnalyzer

class NeckAnalyzer(BaseJointAnalyzer):
    """
    🦴 ANALIZADOR ESPECÍFICO DE CUELLO - HERENCIA COMPLETA
    🎯 Ejercicios: Flexión/Extensión, Rotación, Inclinación lateral
    """
    
    def __init__(self):
        super().__init__(joint_name="NECK")  # ✅ Inicializar base
        
        # 🎯 EJERCICIOS ESPECÍFICOS DE CUELLO
        self.exercise_types = {
            "neck_flexion_extension": "Flexión/Extensión de Cuello",
            "neck_lateral_flexion": "Inclinación Lateral de Cuello", 
            "neck_rotation": "Rotación de Cuello"
        }
        
        # 📊 RANGOS NORMATIVOS (literatura especializada)
        self.normal_ranges = {
            "neck_flexion": {"min": 0, "max": 50, "optimal": 45},
            "neck_extension": {"min": 0, "max": 60, "optimal": 55},
            "neck_lateral_flexion": {"min": 0, "max": 45, "optimal": 40},
            "neck_rotation": {"min": 0, "max": 80, "optimal": 75}
        }
        
        # 🎯 SOPORTE MULTI-EJERCICIO
        self.current_exercise = "flexion"  # Default exercise
    
    def set_current_exercise(self, exercise_type: str):
        """
        Configura el ejercicio actual para el análisis
        
        Args:
            exercise_type: Tipo de ejercicio ('flexion', 'rotation', 'lateral_flexion')
        """
        valid_exercises = ['flexion', 'rotation', 'lateral_flexion']
        if exercise_type in valid_exercises:
            self.current_exercise = exercise_type
            print(f"🎯 Ejercicio de cuello configurado: {exercise_type}")
        else:
            print(f"⚠️ Ejercicio inválido: {exercise_type}. Usando flexion por defecto.")
            self.current_exercise = "flexion"
    
    def get_required_landmarks(self):
        """🎯 IMPLEMENTACIÓN REQUERIDA - Puntos para cuello"""
        return {
            "essential": [0, 11, 12],      # Nariz, hombros
            "recommended": [7, 8, 9, 10],  # Ojos, orejas
            "optional": [1, 2, 3, 4, 5, 6] # Puntos faciales adicionales
        }
    
    def check_required_points_visible(self, landmarks):
        """✅ IMPLEMENTACIÓN REQUERIDA - Verificar visibilidad"""
        required = self.get_required_landmarks()["essential"]
        
        visible_count = 0
        for point_id in required:
            if point_id < len(landmarks) and landmarks[point_id].visibility > 0.6:
                visible_count += 1
        
        return visible_count >= len(required)
    
    def calculate_joint_angles(self, landmarks, frame_shape):
        """
        📐 IMPLEMENTACIÓN REQUERIDA - Cálculo de ángulos específicos
        🎯 Usa toda la funcionalidad base + específico de cuello
        """
        # 🕐 TIMESTAMP base
        result = {
            "segment": self.joint_name,
            "timestamp": self.get_timestamp()
        }
        
        # 🧭 DETECTAR ORIENTACIÓN (usando funcionalidad base)
        orientation_info = self.detect_orientation(landmarks)
        result["orientation_info"] = orientation_info
        
        current_orientation = orientation_info.get("orientation", "UNKNOWN")
        
        # 📐 CÁLCULOS ESPECÍFICOS DE CUELLO
        angles_data = self._calculate_neck_specific_angles(landmarks, frame_shape, current_orientation)
        result.update(angles_data)
        
        # 📊 APLICAR FILTROS BASE (herencia)
        if hasattr(self, '_apply_angle_smoothing') and result.get("primary_angle", 0) > 0:
            result["primary_angle"] = self._apply_angle_smoothing("primary_angle", result["primary_angle"])
        
        return result
    
    def _calculate_neck_specific_angles(self, landmarks, frame_shape, orientation):
        """📐 CÁLCULOS ESPECÍFICOS DE CUELLO por orientación"""
        
        h, w = frame_shape[:2]
        
        # Puntos clave
        nose = landmarks[0]
        l_shoulder = landmarks[11] if len(landmarks) > 11 else None
        r_shoulder = landmarks[12] if len(landmarks) > 12 else None
        
        if not (l_shoulder and r_shoulder):
            return self._get_insufficient_data_result()
        
        # Centro de hombros
        shoulder_center = {
            'x': (l_shoulder.x + r_shoulder.x) / 2,
            'y': (l_shoulder.y + r_shoulder.y) / 2
        }
        
        # Vector cuello
        neck_vector = {
            'x': nose.x - shoulder_center['x'],
            'y': nose.y - shoulder_center['y']
        }
        
        # 🧭 CÁLCULOS SEGÚN ORIENTACIÓN
        if orientation == "SAGITAL":
            return self._calculate_sagittal_neck_angles(neck_vector, nose, shoulder_center)
        elif orientation == "FRONTAL":
            return self._calculate_frontal_neck_angles(neck_vector, nose, shoulder_center, landmarks)
        else:
            return self._calculate_diagonal_neck_angles(neck_vector, nose, shoulder_center)
    
    def _calculate_sagittal_neck_angles(self, neck_vector, nose, shoulder_center):
        """📐 Vista SAGITAL - Flexión/Extensión ULTRA-SENSIBLE"""
        
        # 🎯 UMBRALES MUCHO MÁS BAJOS para detectar movimientos sutiles
        MIN_HORIZONTAL_MOVEMENT = 0.02  # ✅ REDUCIDO de 0.08 a 0.02
        MIN_ANGLE_THRESHOLD = 3.0       # ✅ REDUCIDO de 8.0 a 3.0
        
        # 📐 CÁLCULO MEJORADO
        horizontal_deviation = abs(neck_vector['x'])
        vertical_distance = abs(neck_vector['y'])
        
        # ✅ VERIFICAR SI HAY MOVIMIENTO REAL (más sensible)
        if horizontal_deviation < MIN_HORIZONTAL_MOVEMENT:
            # Cuello está prácticamente recto
            return {
                "exercise_type": "neck_flexion_extension",
                "primary_angle": 0.0,
                "movement_direction": "neutral",
                "neck_flexion_extension": 0.0,
                "assessment": {
                    "status": "NEUTRAL",
                    "angle": 0.0,
                    "recommendation": "Posición neutral - mueve la cabeza adelante/atrás",
                    "percentage": 0
                },
                "optimal_view": "SAGITAL",
                "analysis_quality": "HIGH",
                "angle_details": {
                    "horizontal_deviation": horizontal_deviation,
                    "vertical_distance": vertical_distance,
                    "min_threshold": MIN_HORIZONTAL_MOVEMENT,
                    "movement_detected": False,
                    "calculation_method": "sagittal_ultra_sensitive"
                }
            }
        
        # 📐 CALCULAR ÁNGULO REAL
        if vertical_distance < 0.001:
            angle = 0
        else:
            angle = math.degrees(math.atan2(horizontal_deviation, vertical_distance))
        
        # ✅ APLICAR UMBRAL MÍNIMO MÁS BAJO
        if angle < MIN_ANGLE_THRESHOLD:
            angle = 0
            movement_type = "neutral"
        else:
            # Determinar dirección con umbral más bajo
            if neck_vector['x'] > MIN_HORIZONTAL_MOVEMENT:
                movement_type = "flexion"  # Cabeza adelante
            elif neck_vector['x'] < -MIN_HORIZONTAL_MOVEMENT:
                movement_type = "extension"  # Cabeza atrás
            else:
                movement_type = "neutral"
        
        # Evaluación
        assessment = self._assess_neck_range(movement_type, angle)
        
        return {
            "exercise_type": "neck_flexion_extension",
            "primary_angle": angle,
            "movement_direction": movement_type,
            "neck_flexion_extension": angle,
            "assessment": assessment,
            "optimal_view": "SAGITAL",
            "analysis_quality": "HIGH" if angle > 0 else "MEDIUM",
            "angle_details": {
                "horizontal_deviation": horizontal_deviation,
                "vertical_distance": vertical_distance,
                "raw_angle": math.degrees(math.atan2(horizontal_deviation, vertical_distance)) if vertical_distance > 0.001 else 0,
                "min_threshold": MIN_HORIZONTAL_MOVEMENT,
                "movement_detected": angle > 0,
                "calculation_method": "sagittal_ultra_sensitive"
            }
        }
    
    def _calculate_frontal_neck_angles(self, neck_vector, nose, shoulder_center, landmarks):
        """📐 Vista FRONTAL - SIN COMPENSACIÓN TEMPORAL"""
        
        # 🚨 COMENTAR TEMPORALMENTE LA DETECCIÓN DE COMPENSACIÓN
        # shoulder_compensation = self._detect_shoulder_compensation(landmarks)
        # 
        # if shoulder_compensation["is_compensating"]:
        #     # 🚨 COMPENSACIÓN DETECTADA - NO es movimiento de cuello
        #     return {
        #         "exercise_type": "neck_lateral_flexion",
        #         "primary_angle": 0.0,  # ✅ CERO porque es compensación
        #         "movement_direction": "compensation_detected",
        #         "neck_lateral_flexion": 0.0,
        #         "assessment": {
        #             "status": "COMPENSATION",
        #             "angle": 0.0,
        #             "recommendation": f"⚠️ COMPENSACIÓN: {shoulder_compensation['description']} - Mantén hombros nivelados",
        #             "percentage": 0
        #         },
        #         "optimal_view": "FRONTAL",
        #         "analysis_quality": "COMPENSATION_DETECTED",
        #         "compensation_info": shoulder_compensation,
        #         "angle_details": {
        #             "compensation_angle": shoulder_compensation["angle"],
        #             "movement_detected": False,
        #             "calculation_method": "compensation_filtering"
        #         }
        #     }
        
        # 🎯 PROCEDER DIRECTAMENTE CON CÁLCULO NORMAL
        MIN_LATERAL_DEVIATION = 0.015  # Mantener sensible
        MIN_ANGLE_THRESHOLD = 2.0      # Mantener bajo
        
        lateral_deviation = abs(neck_vector['x'])
        vertical_distance = abs(neck_vector['y'])
        
        # ✅ VERIFICAR MOVIMIENTO (más permisivo)
        if lateral_deviation < MIN_LATERAL_DEVIATION:
            return {
                "exercise_type": "neck_lateral_flexion",
                "primary_angle": 0.0,
                "movement_direction": "neutral",
                "neck_lateral_flexion": 0.0,
                "assessment": {
                    "status": "NEUTRAL",
                    "angle": 0.0,
                    "recommendation": "Posición neutral - inclina la cabeza a los lados",
                    "percentage": 0
                },
                "optimal_view": "FRONTAL",
                "analysis_quality": "HIGH",
                "angle_details": {
                    "lateral_deviation": lateral_deviation,
                    "vertical_distance": vertical_distance,
                    "min_threshold": MIN_LATERAL_DEVIATION,
                    "movement_detected": False,
                    "calculation_method": "frontal_simple_no_compensation"
                }
            }
        
        # 📐 CALCULAR ÁNGULO REAL
        if vertical_distance < 0.001:
            angle = 0
        else:
            angle = math.degrees(math.atan2(lateral_deviation, vertical_distance))
        
        # ✅ APLICAR UMBRAL MÍNIMO
        if angle < MIN_ANGLE_THRESHOLD:
            angle = 0
            movement_type = "neutral"
        else:
            # Determinar dirección
            if neck_vector['x'] > MIN_LATERAL_DEVIATION:
                movement_type = "right"
            elif neck_vector['x'] < -MIN_LATERAL_DEVIATION:
                movement_type = "left"  
            else:
                movement_type = "neutral"
        
        # Evaluación
        assessment = self._assess_neck_range("lateral_flexion", angle)
        
        return {
            "exercise_type": "neck_lateral_flexion",
            "primary_angle": angle,
            "movement_direction": movement_type,
            "neck_lateral_flexion": angle,
            "assessment": assessment,
            "optimal_view": "FRONTAL", 
            "analysis_quality": "HIGH" if angle > 0 else "MEDIUM",
            "angle_details": {
                "lateral_deviation": lateral_deviation,
                "vertical_distance": vertical_distance,
                "raw_angle": math.degrees(math.atan2(lateral_deviation, vertical_distance)) if vertical_distance > 0.001 else 0,
                "min_threshold": MIN_LATERAL_DEVIATION,
                "movement_detected": angle > 0,
                "calculation_method": "frontal_simple_no_compensation"
            }
        }
    
    def _calculate_shoulder_slope(self, landmarks):
        """📐 Calcular inclinación de hombros como referencia"""
        l_shoulder = landmarks[11]
        r_shoulder = landmarks[12]
        
        if abs(r_shoulder.x - l_shoulder.x) > 0.001:
            return math.degrees(math.atan2(
                r_shoulder.y - l_shoulder.y,
                r_shoulder.x - l_shoulder.x
            ))
        return 0
    
    def _assess_neck_range(self, movement_type, angle):
        """📊 Evaluación clínica MEJORADA"""
        
        if angle == 0:
            return {
                "status": "NEUTRAL",
                "angle": 0,
                "recommendation": "Posición neutral - inicia el movimiento gradualmente",
                "percentage": 0
            }
        
        # Rangos específicos por tipo
        if movement_type in ["flexion", "extension"]:
            max_range = 45      # Flexión/extensión
            good_range = 35
            fair_range = 20
        elif movement_type in ["left", "right", "lateral_flexion"]:
            max_range = 40      # Inclinación lateral
            good_range = 30
            fair_range = 15
        else:
            max_range = 40      # General
            good_range = 30
            fair_range = 15
        
        # Evaluación por rangos
        if angle < fair_range:
            status = "INSUFFICIENT"
            recommendation = f"Aumentar rango gradualmente (actual: {angle:.1f}°)"
        elif angle < good_range:
            status = "FAIR"
            recommendation = f"Rango aceptable, puede mejorar hacia {good_range}°"
        elif angle < max_range:
            status = "GOOD"
            recommendation = f"Buen rango de movimiento ({angle:.1f}°)"
        else:
            status = "EXCELLENT"
            recommendation = f"Rango óptimo alcanzado ({angle:.1f}°)"
        
        return {
            "status": status,
            "angle": angle,
            "range_reference": {
                "max": max_range,
                "good": good_range,
                "fair": fair_range
            },
            "recommendation": recommendation,
            "percentage": min(100, (angle / max_range) * 100)
        }
    
    def draw_joint_visualization(self, frame, landmarks, angles):
        """🎨 VISUALIZACIÓN MEJORADA - Con PIL para símbolos correctos"""
        
        if not landmarks or len(landmarks) < 13:
            return frame
        
        overlay = frame.copy()
        h, w = frame.shape[:2]
        
        # Puntos clave
        nose = landmarks[0]
        l_shoulder = landmarks[11]
        r_shoulder = landmarks[12]
        
        # Convertir coordenadas
        nose_px = (int(nose.x * w), int(nose.y * h))
        l_shoulder_px = (int(l_shoulder.x * w), int(l_shoulder.y * h))
        r_shoulder_px = (int(r_shoulder.x * w), int(r_shoulder.y * h))
        shoulder_center_px = (
            int((l_shoulder.x + r_shoulder.x) * w / 2),
            int((l_shoulder.y + r_shoulder.y) * h / 2)
        )
        
        # 📐 INFORMACIÓN DEL ÁNGULO - DEFINIR POSICIONES PRIMERO
        text_x = nose_px[0] + 20
        text_y = nose_px[1] - 40
        
        # Ajustar si está cerca del borde
        if text_x > w - 150:
            text_x = nose_px[0] - 120
        if text_y < 30:
            text_y = nose_px[1] + 30
        
        # 🎨 DIBUJAR ESTRUCTURA CON OPENCV (sin texto)
        # Línea de cuello (más gruesa y visible)
        cv2.line(overlay, shoulder_center_px, nose_px, (0, 255, 255), 4)
        
        # 🚨 VERIFICAR COMPENSACIÓN Y AJUSTAR COLOR DE HOMBROS
        compensation_info = angles.get("compensation_info", {})
        if compensation_info.get("is_compensating", False):
            # Dibujar línea de hombros con color de warning
            cv2.line(overlay, l_shoulder_px, r_shoulder_px, (0, 100, 255), 4)  # Rojo-naranja
            
            # ⚠️ TEXTO DE COMPENSACIÓN (ahora text_x está definido)
            comp_angle = compensation_info.get("angle", 0)
            cv2.putText(overlay, f"COMPENSACION: {comp_angle:.1f}", 
                       (text_x - 20, text_y + 75), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 100, 255), 2)
            cv2.putText(overlay, "NIVELA LOS HOMBROS", 
                       (text_x - 20, text_y + 95), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 2)
        else:
            # Línea de hombros normal (referencia)
            cv2.line(overlay, l_shoulder_px, r_shoulder_px, (255, 255, 0), 3)
        
        # 🎯 PUNTOS CLAVE
        cv2.circle(overlay, nose_px, 10, (0, 0, 255), -1)  # Nariz - rojo
        cv2.circle(overlay, nose_px, 12, (255, 255, 255), 2)  # Borde blanco
        cv2.circle(overlay, shoulder_center_px, 8, (0, 255, 0), -1)  # Centro - verde
        cv2.circle(overlay, l_shoulder_px, 6, (255, 0, 255), -1)  # Hombro izq
        cv2.circle(overlay, r_shoulder_px, 6, (255, 0, 255), -1)  # Hombro der
        
        # Combinar overlay inicial
        alpha = 0.8
        frame = cv2.addWeighted(frame, alpha, overlay, 1 - alpha, 0)
        
        # 📐 USAR PIL PARA TEXTO CON SÍMBOLOS (solo si NO hay compensación)
        if not compensation_info.get("is_compensating", False):
            frame = self._draw_angle_text_with_pil(frame, angles, nose_px, shoulder_center_px)
        else:
            # Si hay compensación, mostrar mensaje simple
            primary_angle = angles.get("primary_angle", 0)
            movement_dir = angles.get("movement_direction", "neutral")
            
            # Texto básico con OpenCV para compensación
            cv2.putText(frame, f"{primary_angle:.1f} - COMPENSATION", 
                       (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 2)
            cv2.putText(frame, f"Status: {movement_dir.upper()}", 
                       (text_x, text_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        
        return frame

    def _draw_angle_text_with_pil(self, frame, angles, nose_px, shoulder_center_px):
        """📐 Dibujar texto con PIL para símbolos correctos"""
        
        # 🔄 CONVERTIR A PIL
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
        
        # Convertir BGR a RGB para PIL
        pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)
        
        # 🎯 CARGAR FUENTE
        try:
            # Intentar cargar fuente del sistema
            font_large = ImageFont.truetype("arial.ttf", 24)
            font_medium = ImageFont.truetype("arial.ttf", 18)
            font_small = ImageFont.truetype("arial.ttf", 14)
        except:
            # Fuente por defecto si no encuentra arial
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # 📐 INFORMACIÓN DEL ÁNGULO
        primary_angle = angles.get("primary_angle", 0)
        movement_dir = angles.get("movement_direction", "neutral")
        
        # 🎯 POSICIÓN DEL TEXTO - CERCA DE LA CABEZA
        text_x = nose_px[0] + 20
        text_y = nose_px[1] - 40
        
        # Ajustar si está cerca del borde
        if text_x > frame.shape[1] - 150:
            text_x = nose_px[0] - 120
        if text_y < 30:
            text_y = nose_px[1] + 30
        
        # 📊 FONDO PARA TEXTO
        bbox_width = 120
        bbox_height = 70
        
        # Fondo semi-transparente
        bbox = [text_x - 5, text_y - 10, text_x + bbox_width, text_y + bbox_height]
        draw.rectangle(bbox, fill=(0, 0, 0, 180), outline=(255, 255, 255, 255), width=2)
        
        # 🎯 TEXTO PRINCIPAL - ÁNGULO CON SÍMBOLO CORRECTO
        if primary_angle > 0:
            angle_text = f"{primary_angle:.1f}°"  # ✅ PIL mostrará el símbolo correctamente
            draw.text((text_x, text_y), angle_text, font=font_large, fill=(0, 255, 255, 255))
            
            # 📍 TIPO DE MOVIMIENTO
            if movement_dir not in ["neutral", "unknown"]:
                movement_text = f"{movement_dir.upper()}"
                draw.text((text_x, text_y + 30), movement_text, font=font_medium, fill=(255, 255, 0, 255))
        else:
            draw.text((text_x, text_y), "0.0°", font=font_large, fill=(128, 128, 128, 255))
            draw.text((text_x, text_y + 30), "NEUTRAL", font=font_medium, fill=(128, 128, 128, 255))
        
        # 📊 EVALUACIÓN
        assessment = angles.get("assessment", {})
        if assessment.get("status"):
            status = assessment["status"]
            status_colors = {
                "EXCELLENT": (0, 255, 0, 255),
                "GOOD": (0, 255, 255, 255),
                "FAIR": (0, 165, 255, 255),
                "INSUFFICIENT": (255, 0, 0, 255),
                "NEUTRAL": (128, 128, 128, 255)
            }
            status_color = status_colors.get(status, (255, 255, 255, 255))
            draw.text((text_x, text_y + 50), status[:8], font=font_small, fill=status_color)
        
        # 🔄 ORIENTACIÓN
        current_orientation = angles.get("orientation_info", {}).get("orientation", "")
        optimal_view = angles.get("optimal_view", "")
        
        if current_orientation != optimal_view and optimal_view:
            draw.text((shoulder_center_px[0] - 50, shoulder_center_px[1] + 20), 
                     f"Vista: {current_orientation}", font=font_small, fill=(255, 255, 0, 255))
            draw.text((shoulder_center_px[0] - 50, shoulder_center_px[1] + 35), 
                     f"Ideal: {optimal_view}", font=font_small, fill=(0, 255, 255, 255))
        
        # 🔄 CONVERTIR DE VUELTA A OPENCV
        frame_with_text = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        return frame_with_text

    def debug_angles_info(self, angles, fps_counter, current_view):
        """🔧 Información de depuración MEJORADA"""
        
        angle_details = angles.get("angle_details", {})
        if fps_counter % 30 == 0:  # Debug cada segundo
            print(f"🔍 DEBUG MEJORADO:")
            print(f"  Vista: {current_view}")
            print(f"  Ángulo final: {angles.get('primary_angle', 0):.1f}°")
            print(f"  Movimiento: {angles.get('movement_direction', 'none')}")
            print(f"  Desviación horizontal: {angle_details.get('horizontal_deviation', 0):.3f}")
            print(f"  Distancia vertical: {angle_details.get('vertical_distance', 0):.3f}")
            print(f"  Movimiento detectado: {angle_details.get('movement_detected', False)}")
            print("-" * 50)
    
    def _detect_shoulder_compensation(self, landmarks):
        """🚨 DETECTA si el usuario está inclinando todo el torso - CON DEBUG"""
        
        l_shoulder = landmarks[11]
        r_shoulder = landmarks[12]
        
        # 📐 Calcular inclinación de la línea de hombros
        if abs(r_shoulder.x - l_shoulder.x) > 0.001:
            shoulder_slope_angle = abs(math.degrees(math.atan2(
                r_shoulder.y - l_shoulder.y,
                r_shoulder.x - l_shoulder.x
            )))
        else:
            shoulder_slope_angle = 0
        
        # 🔍 DEBUG TEMPORAL
        print(f"🔍 DEBUG COMPENSACIÓN: Ángulo hombros = {shoulder_slope_angle:.1f}°")
        
        # 🚨 UMBRALES MUY ALTOS TEMPORALMENTE
        COMPENSATION_THRESHOLD = 25.0   # ✅ MUY ALTO
        SEVERE_COMPENSATION = 40.0      # ✅ MUY ALTO
        
        if shoulder_slope_angle > SEVERE_COMPENSATION:
            print(f"🚨 COMPENSACIÓN SEVERA detectada: {shoulder_slope_angle:.1f}°")
            return {
                "is_compensating": True,
                "severity": "SEVERE", 
                "angle": shoulder_slope_angle,
                "description": f"Inclinación corporal severa ({shoulder_slope_angle:.1f}°)"
            }
        elif shoulder_slope_angle > COMPENSATION_THRESHOLD:
            print(f"⚠️ COMPENSACIÓN MODERADA detectada: {shoulder_slope_angle:.1f}°")
            return {
                "is_compensating": True,
                "severity": "MODERATE",
                "angle": shoulder_slope_angle, 
                "description": f"Inclinación corporal moderada ({shoulder_slope_angle:.1f}°)"
            }
        else:
            print(f"✅ HOMBROS OK: {shoulder_slope_angle:.1f}° - Permitir movimiento")
            return {
                "is_compensating": False,
                "severity": "NONE",
                "angle": shoulder_slope_angle,
                "description": "Hombros aceptables - movimiento válido"
            }
    
    def _get_insufficient_data_result(self):
        """📊 Resultado cuando no hay datos suficientes"""
        return {
            "exercise_type": "neck_unknown",
            "primary_angle": 0,
            "movement_direction": "unknown",
            "assessment": {"status": "INSUFFICIENT_DATA", "recommendation": "Mejorar visibilidad de landmarks"},
            "optimal_view": "UNKNOWN",
            "analysis_quality": "POOR"
        }

    def _calculate_diagonal_neck_angles(self, neck_vector, nose, shoulder_center):
        """📐 Vista DIAGONAL - Análisis limitado"""
        
        angle = abs(math.degrees(math.atan2(abs(neck_vector['x']), abs(neck_vector['y']))))
        
        return {
            "exercise_type": "neck_general",
            "primary_angle": angle,
            "movement_direction": "diagonal",
            "assessment": {"status": "SUBOPTIMAL", "recommendation": "Ajustar a vista SAGITAL o FRONTAL"},
            "optimal_view": "SAGITAL_OR_FRONTAL",
            "analysis_quality": "LOW"
        }