"""
🦴 GUÍA ESPECÍFICA para ejercicios de CUELLO
🎯 Flexión/Extensión, Inclinación lateral, Rotación
"""

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from core.exercise_guide_base import ExerciseGuideManager
from typing import Dict, List

class NeckExerciseGuide(ExerciseGuideManager):
    """
    🦴 GUÍA ESPECÍFICA para ejercicios de CUELLO
    🎯 Flexión/Extensión, Inclinación lateral, Rotación
    """
    
    def __init__(self):
        super().__init__("NECK")
    
    def _get_exercises_config(self) -> Dict:
        """🎯 Configuración específica para cuello"""
        return {
            "neck_flexion_extension": {
                "name": "Flexión/Extensión de Cuello",
                "primary_view": "SAGITAL",
                "secondary_view": "FRONTAL",
                "critical_angles": [30, 45, 60],
                "compensation_risks": ["elevacion_hombros", "rotacion_tronco"],
                "bilateral_validation": "OPTIONAL"
            },
            
            "neck_lateral_flexion": {
                "name": "Inclinación Lateral de Cuello",
                "primary_view": "FRONTAL",
                "secondary_view": "SAGITAL", 
                "critical_angles": [20, 35, 45],
                "compensation_risks": ["elevacion_hombro_unilateral", "inclinacion_tronco"],
                "bilateral_validation": "RECOMMENDED"
            },
            
            "neck_rotation": {
                "name": "Rotación de Cuello",
                "primary_view": "FRONTAL",
                "secondary_view": None,
                "critical_angles": [45, 65, 80],
                "compensation_risks": ["rotacion_tronco", "elevacion_hombros"],
                "bilateral_validation": "OPTIONAL"
            }
        }
    
    def _predict_basic_compensations(self, exercise_type: str, maximized: Dict) -> List[str]:
        """🚨 COMPENSACIONES ESPECÍFICAS DEL CUELLO"""
        compensations = []
        primary_angle = maximized.get("primary_angle", 0)
        
        if exercise_type == "neck_flexion_extension":
            if primary_angle > 50:  # Rango alto
                compensations.append("⚠️ Rango alto - revisar elevación de hombros")
                
        elif exercise_type == "neck_lateral_flexion":
            if primary_angle > 35:
                compensations.append("⚠️ Inclinación alta - revisar elevación de hombro")
                
        elif exercise_type == "neck_rotation":
            if primary_angle > 70:
                compensations.append("⚠️ Rotación extrema - revisar compensación de tronco")
        
        return compensations
    
    def _maximize_visible_simple(self, exercise_type: str, analysis_data: Dict) -> Dict:
        """🎯 MAXIMIZAR análisis de cuello"""
        maximized = {
            "primary_angle": 0,
            "side_analyzed": "bilateral",
            "quality_score": 0.0
        }
        
        # Extraer ángulo principal según ejercicio
        if exercise_type == "neck_flexion_extension":
            angle = analysis_data.get("neck_flexion_extension", 0)
            maximized["primary_angle"] = angle
            
        elif exercise_type == "neck_lateral_flexion":
            angle = analysis_data.get("neck_lateral_flexion", 0)
            maximized["primary_angle"] = angle
            
        elif exercise_type == "neck_rotation":
            angle = analysis_data.get("neck_rotation", 0)
            maximized["primary_angle"] = angle
        
        # Calcular calidad
        if maximized["primary_angle"] > 0:
            maximized["quality_score"] = 0.9  # Cuello generalmente tiene buena detección
        else:
            maximized["quality_score"] = 0.4
        
        return maximized