"""
🧠 SISTEMA BASE DE GUÍA INTELIGENTE
🛡️ CONSERVADOR: No modifica nada existente
🎯 Solo AGREGA funcionalidad nueva
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import time

class ExerciseGuideManager:
    """
    🎯 MANAGER SIMPLE - PUNTO DE ENTRADA ÚNICO
    🛡️ CONSERVADOR: Funciona con tu código actual SIN CAMBIOS
    """
    
    def __init__(self, segment_name: str):
        self.segment_name = segment_name
        
        # 🕐 HISTORIAL SIMPLE para combinar vistas
        self.view_history = {}
        
        # 🎯 CONFIGURACIÓN por segmento
        self.exercises_config = self._get_exercises_config()
        
        # ⏱️ Control temporal MEJORADO
        self.last_guidance_time = 0
        self.guidance_cooldown = 0.5  # 🆕 REDUCIR de 2.0 a 0.5 segundos
    
        # 🆕 PERSISTENCIA DE MENSAJES
        self.persistent_messages = {
            "last_guidance": None,
            "last_update_time": 0,
            "message_duration": 3.0  # Mantener mensajes por 3 segundos
        }

    def analyze_with_guidance(self, exercise_type: str, current_view: str, 
                            analysis_data: Dict, landmarks) -> Dict:
        """
        🧠 FUNCIÓN PRINCIPAL con MENSAJES PERSISTENTES
        """
        current_time = time.time()
        
        # 🆕 LÓGICA DE PERSISTENCIA
        use_cached_guidance = (
            current_time - self.last_guidance_time < self.guidance_cooldown and
            self.persistent_messages["last_guidance"] is not None
        )
        
        if use_cached_guidance:
            # Usar mensajes anteriores pero actualizar datos básicos
            cached_guidance = self.persistent_messages["last_guidance"].copy()
            cached_guidance["original_analysis"] = analysis_data  # Actualizar datos
            return cached_guidance
        
        # 🔄 GENERAR NUEVA GUÍA
        self.last_guidance_time = current_time
        
        # 🎯 PRINCIPIO 1: Acepta limitaciones de una cámara
        limitations = self._assess_simple_limitations(current_view)
        
        # 🎯 PRINCIPIO 2: Maximiza análisis del lado visible
        maximized = self._maximize_visible_simple(exercise_type, analysis_data)
        
        # 🎯 PRINCIPIO 3: Predice compensaciones (BÁSICO)
        predicted_compensations = self._predict_basic_compensations(exercise_type, maximized)
        
        # 🎯 PRINCIPIO 4: Guía para vistas complementarias
        view_guidance = self._generate_simple_guidance(exercise_type, current_view, maximized)
        
        # 🎯 PRINCIPIO 5: Combina datos temporales (SIMPLE)
        self._update_simple_history(exercise_type, current_view, maximized)
        
        result = {
            "original_analysis": analysis_data,
            "guidance_available": True,
            
            # Nuevas funcionalidades
            "current_limitations": limitations,
            "maximized_analysis": maximized,
            "predicted_compensations": predicted_compensations,
            "view_guidance": view_guidance,
            
            # Métricas simples
            "analysis_confidence": self._calculate_simple_confidence(maximized),
            "next_recommendation": view_guidance.get("next_action", "Continúa")
        }
        
        # 🆕 GUARDAR PARA PERSISTENCIA
        self.persistent_messages["last_guidance"] = result.copy()
        self.persistent_messages["last_update_time"] = current_time
        
        return result
    
    def _get_exercises_config(self) -> Dict:
        """🎯 Configuración simple por segmento"""
        if self.segment_name == "SHOULDER":
            return {
                "shoulder_flexion": {
                    "name": "Flexión de Hombro",
                    "primary_view": "SAGITAL",
                    "secondary_view": "FRONTAL",
                    "critical_compensations": ["trunk_inclination", "scapular_elevation"]
                },
                "shoulder_abduction": {
                    "name": "Abducción de Hombro", 
                    "primary_view": "FRONTAL",
                    "secondary_view": "SAGITAL",
                    "critical_compensations": ["lateral_flexion", "asymmetry"]
                }
            }
        
        # Otros segmentos se agregarán después
        return {}
    
    def _assess_simple_limitations(self, current_view: str) -> Dict:
        """🔍 PRINCIPIO 1: Limitaciones simples"""
        limitations = {
            "view_type": current_view,
            "bilateral_limited": current_view == "SAGITAL",
            "depth_limited": current_view == "FRONTAL",
            "recommendation": ""
        }
        
        if current_view == "SAGITAL":
            limitations["recommendation"] = "Un lado puede estar oculto"
        elif current_view == "FRONTAL":
            limitations["recommendation"] = "Información de profundidad limitada"
        
        return limitations
    
    def _maximize_visible_simple(self, exercise_type: str, analysis_data: Dict) -> Dict:
        """🎯 PRINCIPIO 2: Maximizar lado visible (simple)"""
        maximized = {
            "primary_angle": 0,
            "side_analyzed": "unknown",
            "quality_score": 0.0
        }
        
        # Extraer ángulo principal según ejercicio
        if exercise_type == "shoulder_flexion":
            if "right_shoulder_flexion" in analysis_data:
                maximized["primary_angle"] = analysis_data["right_shoulder_flexion"]
                maximized["side_analyzed"] = "right"
            elif "left_shoulder_flexion" in analysis_data:
                maximized["primary_angle"] = analysis_data["left_shoulder_flexion"]  
                maximized["side_analyzed"] = "left"
        
        elif exercise_type == "shoulder_abduction":
            # Similar para abducción cuando se implemente
            maximized["primary_angle"] = analysis_data.get("shoulder_separation", 0)
            maximized["side_analyzed"] = "bilateral"
        
        # Calcular calidad simple
        if maximized["primary_angle"] > 0:
            maximized["quality_score"] = 0.8  # Datos disponibles
        else:
            maximized["quality_score"] = 0.3  # Datos limitados
        
        return maximized
    
    def _predict_basic_compensations(self, exercise_type: str, maximized: Dict) -> List[str]:
        """🚨 PRINCIPIO 3: Compensaciones básicas"""
        compensations = []
        
        primary_angle = maximized.get("primary_angle", 0)
        
        if exercise_type == "shoulder_flexion":
            if primary_angle > 120:
                compensations.append("⚠️ Rango alto - revisar compensaciones de tronco")
            if primary_angle > 150:
                compensations.append("⚠️ Rango extremo - probable elevación escapular")
        
        elif exercise_type == "shoulder_abduction":
            if primary_angle > 90:
                compensations.append("⚠️ Revisar flexión lateral de tronco")
        
        return compensations
    
    def _generate_simple_guidance(self, exercise_type: str, current_view: str, maximized: Dict) -> Dict:
        """🎯 PRINCIPIO 4: Guía simple"""
        config = self.exercises_config.get(exercise_type, {})
        
        guidance = {
            "current_view_status": "UNKNOWN",
            "next_action": "Continúa",
            "instructions": []
        }
        
        primary_view = config.get("primary_view", "")
        secondary_view = config.get("secondary_view", "")
        
        if current_view == primary_view:
            guidance["current_view_status"] = "OPTIMAL"
            guidance["instructions"].append(f"✅ Vista {primary_view} correcta")
            
            # Determinar si necesita cambio
            if maximized.get("quality_score", 0) > 0.7:
                needs_validation = self._needs_secondary_validation(exercise_type, maximized)
                if needs_validation:
                    guidance["next_action"] = f"Gira a {secondary_view} para validar"
                    guidance["instructions"].append(f"🔄 Siguiente: vista {secondary_view}")
        
        elif current_view == secondary_view:
            guidance["current_view_status"] = "VALIDATING"
            guidance["instructions"].append(f"⚖️ Validando en {secondary_view}")
            guidance["next_action"] = f"Regresa a {primary_view}"
        
        else:
            guidance["current_view_status"] = "SUBOPTIMAL"
            guidance["instructions"].append(f"🎯 Mejor vista: {primary_view}")
            guidance["next_action"] = f"Cambia a {primary_view}"
        
        return guidance
    
    def _needs_secondary_validation(self, exercise_type: str, maximized: Dict) -> bool:
        """🔍 Determina si necesita validación secundaria"""
        primary_angle = maximized.get("primary_angle", 0)
        
        # Rangos donde típicamente se necesita validación bilateral
        if exercise_type == "shoulder_flexion" and primary_angle > 120:
            return True
        
        return False
    
    def _update_simple_history(self, exercise_type: str, current_view: str, analysis: Dict):
        """🕐 PRINCIPIO 5: Historial simple"""
        if exercise_type not in self.view_history:
            self.view_history[exercise_type] = {}
        
        if current_view not in self.view_history[exercise_type]:
            self.view_history[exercise_type][current_view] = []
        
        # Mantener últimas 10 entradas
        history = self.view_history[exercise_type][current_view]
        history.append({
            "timestamp": time.time(),
            "primary_angle": analysis.get("primary_angle", 0),
            "quality": analysis.get("quality_score", 0)
        })
        
        if len(history) > 10:
            history.pop(0)
    
    def _calculate_simple_confidence(self, maximized: Dict) -> float:
        """📊 Confianza simple"""
        base_confidence = maximized.get("quality_score", 0.0)
        
        # Bonus por ángulos en rangos válidos
        angle = maximized.get("primary_angle", 0)
        if 30 <= angle <= 180:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def _get_basic_status(self, current_view: str, exercise_type: str) -> str:
        """📋 Estado básico cuando no hay guía completa"""
        config = self.exercises_config.get(exercise_type, {})
        primary_view = config.get("primary_view", "")
        
        if current_view == primary_view:
            return f"✅ Vista óptima para {exercise_type}"
        else:
            return f"🔄 Vista recomendada: {primary_view}"

# 🎯 FUNCIÓN DE CONVENIENCIA para uso fácil
def create_exercise_guide(segment_name: str) -> ExerciseGuideManager:
    """🚀 Crea guía para el segmento especificado"""
    return ExerciseGuideManager(segment_name)