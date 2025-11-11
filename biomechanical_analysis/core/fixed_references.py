"""
📐 REFERENCIAS FIJAS ESPACIALES PARA MEDICIONES BIOMECÁNICAS
🎯 Líneas fijas en el espacio que NO se mueven con compensaciones

⚠️ TODO TÉCNICO (después de validar codo):
   - knee_flexion actualmente usa VERTICAL_REFERENCE (↑)
   - Biomecánicamente debería usar VERTICAL_DOWN_REFERENCE (↓)
   - Esperar validación del fix de codo antes de aplicar cambio similar
"""

import math
import numpy as np
import cv2

class FixedSpatialReferences:
    """
    📐 SISTEMA DE REFERENCIAS FIJAS
    🎯 Líneas inmóviles en el espacio para mediciones precisas
    """
    
    def __init__(self):
        # 📐 REFERENCIAS ESPACIALES BÁSICAS
        self.VERTICAL_REFERENCE = {"x": 0, "y": -1}      # Vector vertical hacia arriba
        self.VERTICAL_DOWN_REFERENCE = {"x": 0, "y": 1}  # 🆕 Vector vertical hacia ABAJO (para codo)
        self.HORIZONTAL_REFERENCE = {"x": 1, "y": 0}     # Vector horizontal derecha
        self.GRAVITY_LINE = {"angle": 90}                # Línea de gravedad (90°)
        
    def get_fixed_reference_vector(self, orientation, exercise_type):
        """🎯 Obtener vector de referencia fijo según orientación y ejercicio"""
        
        references = {
            # VISTA SAGITAL (de perfil) - Flexión/Extensión
            "SAGITAL": {
                "shoulder_flexion": self.VERTICAL_REFERENCE,     # Flexión: vs vertical (brazo sube hacia arriba)
                "shoulder_extension": self.VERTICAL_REFERENCE,   # Extensión: vs vertical (brazo baja hacia atrás)
                "elbow_flexion": self.VERTICAL_REFERENCE,        # 🔧 CRÍTICO: vs vertical ARRIBA (0°=brazo recto, 145°=flexión) - inversión automática línea 87
                "elbow_extension": self.VERTICAL_REFERENCE,      # 🔧 CRÍTICO: vs vertical ARRIBA (0°=brazo recto, 145°=flexión) - inversión automática línea 87
                "neck_flexion_extension": self.VERTICAL_REFERENCE,
                "hip_flexion": self.VERTICAL_REFERENCE,
                "knee_flexion": self.VERTICAL_REFERENCE,         # 🦵 RODILLA: vs vertical (pierna sube hacia atrás)
                "knee_extension": self.VERTICAL_REFERENCE        # 🦵 RODILLA: vs vertical (pierna baja, extensión completa)
            },
            
            # VISTA FRONTAL (de frente) - Abducción/Aducción
            "FRONTAL": {
                "shoulder_abduction": self.VERTICAL_REFERENCE,   # ✅ CORRECCIÓN: vs vertical (brazo sube hacia arriba lateralmente)
                "shoulder_adduction": self.VERTICAL_REFERENCE,   # ✅ CORRECCIÓN: vs vertical
                "neck_lateral_flexion": self.VERTICAL_REFERENCE,
                "hip_abduction": self.VERTICAL_REFERENCE,        # ✅ CORRECCIÓN: vs vertical (paciente de pie, pierna vs gravedad)
                "hip_adduction": self.VERTICAL_REFERENCE,        # ✅ CORRECCIÓN: vs vertical (paciente de pie, pierna vs gravedad)
                "ankle_inversion": self.VERTICAL_REFERENCE
            }
        }
        
        return references.get(orientation, {}).get(exercise_type, self.VERTICAL_REFERENCE)
    
    def calculate_angle_with_fixed_reference(self, segment_vector, orientation, exercise_type):
        """
        📐 CÁLCULO PRECISO: Ángulo entre segmento móvil y referencia fija
        🎯 NO se ve afectado por compensaciones corporales
        """
        
        # 🎯 Obtener referencia fija
        fixed_ref = self.get_fixed_reference_vector(orientation, exercise_type)
        
        # 📐 Calcular ángulo entre vectores
        # Fórmula: cos(θ) = (A·B) / (|A|*|B|)
        
        # Producto punto
        dot_product = (segment_vector["x"] * fixed_ref["x"] + 
                      segment_vector["y"] * fixed_ref["y"])
        
        # Magnitudes
        segment_magnitude = math.sqrt(segment_vector["x"]**2 + segment_vector["y"]**2)
        ref_magnitude = math.sqrt(fixed_ref["x"]**2 + fixed_ref["y"]**2)
        
        if segment_magnitude == 0 or ref_magnitude == 0:
            return 0
        
        # Ángulo en radianes
        cos_angle = dot_product / (segment_magnitude * ref_magnitude)
        cos_angle = max(-1, min(1, cos_angle))  # Clamp para evitar errores numéricos
        
        angle_rad = math.acos(cos_angle)
        angle_deg = math.degrees(angle_rad)
        
        # 🔄 INVERTIR para estándar goniométrico
        # arccos da: 0° (paralelo arriba) → 180° (paralelo abajo)
        # Goniometría quiere: 0° (abajo) → 180° (arriba)
        angle_deg = 180 - angle_deg
        
        return angle_deg
    
    def draw_fixed_reference_lines(self, frame, orientation, exercise_type, center_point):
        """
        🎨 DIBUJAR líneas de referencia fijas en pantalla
        🎯 Visualizar las referencias espaciales que se usan
        """
        
        h, w = frame.shape[:2]
        center_x, center_y = center_point
        
        # 📏 LONGITUD DE LÍNEAS DE REFERENCIA (más largas para mejor visibilidad)
        line_length = min(w, h) // 4  # Era //6, ahora //4 (más largo)
        
        # 🎨 COLORES MÁS VISIBLES
        LINE_COLOR = (0, 255, 255)  # AMARILLO BRILLANTE (era rojo tenue)
        TEXT_COLOR = (0, 255, 255)  # AMARILLO BRILLANTE
        LINE_THICKNESS = 3  # Más grueso (era 2)
        
        if orientation == "SAGITAL":
            if "flexion" in exercise_type or "extension" in exercise_type:
                # ✅ DESHABILITADO: Línea de referencia no es necesaria para codo
                # El cálculo usa método de 3 puntos (hombro-codo-muñeca), NO referencia vertical
                
                # 🎯 Solo dibujar para hombro, cadera, etc. (NO para codo)
                if "elbow" not in exercise_type:
                    # Línea VERTICAL de referencia
                    start_point = (center_x, center_y - line_length)
                    end_point = (center_x, center_y + line_length)
                    cv2.line(frame, start_point, end_point, LINE_COLOR, LINE_THICKNESS)
                    label = "REF VERTICAL"  # Hombro, cadera, etc.
                    cv2.putText(frame, label, (center_x + 10, center_y - line_length + 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, TEXT_COLOR, 2)
                
        elif orientation == "FRONTAL":
            # Comentado - ejecuta cada frame, no necesario para producción
            # print(f"🚨 FRONTAL DEBUG - exercise_type = '{exercise_type}'")
            # print(f"   - Contains 'abduction'? {'abduction' in exercise_type}")
            # print(f"   - Contains 'adduction'? {'adduction' in exercise_type}")
            if "abduction" in exercise_type or "adduction" in exercise_type:
                # FIX: Línea VERTICAL de referencia (paciente de pie, eje = gravedad)
                # Según Norkin & White: "Patient standing, reference is vertical line"
                start_point = (center_x, center_y - line_length)
                end_point = (center_x, center_y + line_length)
                cv2.line(frame, start_point, end_point, LINE_COLOR, LINE_THICKNESS)
                cv2.putText(frame, "REF VERTICAL", (center_x + 10, center_y - line_length + 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, TEXT_COLOR, 2)
                # Comentado - ejecuta cada frame, no necesario
                # print(f"✅ Dibujado eje VERTICAL (frontal abduction/adduction - paciente de pie)")
            
            elif "lateral" in exercise_type:
                # Línea VERTICAL de referencia para inclinación lateral
                start_point = (center_x, center_y - line_length)
                end_point = (center_x, center_y + line_length) 
                cv2.line(frame, start_point, end_point, LINE_COLOR, LINE_THICKNESS)
                cv2.putText(frame, "REF VERTICAL", (center_x + 10, center_y - line_length + 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, TEXT_COLOR, 2)
        
        elif orientation == "TRANSVERSAL" or orientation == "TRANSVERSO":
            # 🆕 VISTA TRANSVERSAL (desde arriba) - para rotaciones
            if "rotation" in exercise_type or "pronation" in exercise_type or "supination" in exercise_type:
                # Dibujar cruz de referencia (+ en centro)
                # Línea HORIZONTAL
                start_h = (center_x - line_length, center_y)
                end_h = (center_x + line_length, center_y)
                cv2.line(frame, start_h, end_h, LINE_COLOR, LINE_THICKNESS)
                
                # Línea VERTICAL
                start_v = (center_x, center_y - line_length)
                end_v = (center_x, center_y + line_length)
                cv2.line(frame, start_v, end_v, LINE_COLOR, LINE_THICKNESS)
                
                # Texto
                cv2.putText(frame, "REF TRANSVERSAL", (center_x + 10, center_y - line_length + 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, TEXT_COLOR, 2)
        
        else:
            # 🆕 FALLBACK: Para orientaciones DIAGONAL, UNKNOWN, etc.
            # Dibujar línea VERTICAL por defecto (movimiento sagital es más común)
            # Comentado - ejecuta cada frame, solo advertencia
            # print(f"⚠️ Orientación '{orientation}' no reconocida, usando VERTICAL por defecto")
            start_point = (center_x, center_y - line_length)
            end_point = (center_x, center_y + line_length)
            cv2.line(frame, start_point, end_point, LINE_COLOR, LINE_THICKNESS)
            cv2.putText(frame, f"REF ({orientation})", (center_x + 10, center_y - line_length + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, TEXT_COLOR, 2)
        
        # 🔍 DEBUG: Comentado - ejecuta cada frame, no necesario
        # print(f"🎨 draw_fixed_reference_lines() - Orientación: {orientation}, Ejercicio: {exercise_type}")
        
        return frame
    
    def validate_measurement_quality(self, angle, segment_vector, orientation, exercise_type):
        """
        ✅ VALIDAR calidad de medición con referencia fija
        🎯 Determinar si el ángulo es confiable
        """
        
        # Verificar que el segmento tenga longitud suficiente
        segment_length = math.sqrt(segment_vector["x"]**2 + segment_vector["y"]**2)
        
        if segment_length < 0.1:  # Segmento muy corto
            return {
                "quality": "POOR",
                "reason": "Segmento muy corto para medición confiable",
                "confidence": 0.3
            }
        
        # Verificar orientación óptima
        optimal_orientations = {
            "shoulder_flexion": ["SAGITAL"],
            "shoulder_abduction": ["FRONTAL", "SAGITAL"],
            "neck_flexion_extension": ["SAGITAL"],
            "neck_lateral_flexion": ["FRONTAL"]
        }
        
        if exercise_type in optimal_orientations:
            if orientation not in optimal_orientations[exercise_type]:
                return {
                    "quality": "SUBOPTIMAL", 
                    "reason": f"Vista {orientation} no ideal para {exercise_type}",
                    "confidence": 0.6
                }
        
        # Medición de buena calidad
        return {
            "quality": "HIGH",
            "reason": "Referencia fija con orientación óptima",
            "confidence": 0.95
        }