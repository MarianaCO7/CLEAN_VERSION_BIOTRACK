# core/orientation_detector.py

import numpy as np
import math

class AdaptiveOrientationDetector:
    """
    🧠 DETECTOR DE ORIENTACIÓN CORPORAL
    🎯 Basado en ESTRUCTURA CORPORAL, NO en movimientos de brazos
    """
    
    def __init__(self):
        self.orientation_history = []
        
        # 🎯 LANDMARKS ULTRA ESTABLES - SOLO TORSO Y CADERAS
        self.orientation_landmarks = {
            "CORE_BODY_ONLY": [11, 12, 23, 24],  # SOLO hombros + caderas
            "HIPS_ONLY": [23, 24],  # SOLO caderas (MÁS estable)
            "TORSO_MINIMAL": [11, 12, 23, 24, 0],  # + cabeza si está
        }
        
        # 🎯 UMBRALES MÁS CONSERVADORES
        self.orientation_thresholds = {
            "FRONTAL_STRONG": 2.2,      # 🆕 CORREGIDO - era 3.2
            "FRONTAL_WEAK": 1.8,        # 🆕 CORREGIDO - era 2.8  
            "SAGITAL_STRONG": 0.8,      # ← Mantener
            "SAGITAL_EXTENDED": 1.2,    # 🆕 AJUSTADO - era 1.5
            "DIAGONAL_ZONE": (1.2, 1.8) # 🆕 ZONA MÁS PEQUEÑA - era (1.5, 2.8)
        }
    
    def detect_orientation_adaptive(self, landmarks):
        """
        🧠 DETECCIÓN BASADA EN ESTRUCTURA CORPORAL ESTABLE
        🚫 IGNORA movimientos de brazos
        """
        try:
            # 🔍 Evaluar landmarks ESTABLES disponibles
            available_sets = self._evaluate_stable_landmarks(landmarks)
            
            # 🎯 Usar el mejor conjunto estable
            best_set = self._select_best_stable_set(available_sets)
            
            if not best_set:
                return self._insufficient_orientation_data()
            
            # 📐 Calcular orientación SOLO con estructura corporal
            orientation_metrics = self._calculate_stable_orientation_metrics(landmarks, best_set)
            
            # 🎯 Clasificar orientación
            orientation_result = self._classify_stable_orientation(orientation_metrics)
            
            # 🔄 Aplicar filtro temporal MÁS FUERTE
            stabilized_result = self._apply_strong_orientation_filter(orientation_result)
            
            return {
                **stabilized_result,
                "landmark_set_used": best_set["name"],
                "landmark_count": best_set["count"],
                "metrics": orientation_metrics
            }
            
        except Exception as e:
            return self._error_response(str(e))
    
    def _evaluate_stable_landmarks(self, landmarks):
        """
        🔍 EVALÚA solo landmarks ESTABLES (no brazos)
        """
        available_sets = {}
        
        for set_name, landmark_ids in self.orientation_landmarks.items():
            visible_landmarks = []
            total_visibility = 0
            
            for landmark_id in landmark_ids:
                if landmark_id < len(landmarks) and landmarks[landmark_id].visibility > 0.6:
                    visible_landmarks.append(landmark_id)
                    total_visibility += landmarks[landmark_id].visibility
            
            coverage = len(visible_landmarks) / len(landmark_ids)
            avg_visibility = total_visibility / len(visible_landmarks) if visible_landmarks else 0
            quality_score = coverage * avg_visibility
            
            available_sets[set_name] = {
                "name": set_name,
                "landmarks": visible_landmarks,
                "count": len(visible_landmarks),
                "coverage": coverage,
                "avg_visibility": avg_visibility,
                "quality_score": quality_score,
                "usable": coverage >= 0.75  # Más restrictivo para estabilidad
            }
        
        return available_sets
    
    def _select_best_stable_set(self, available_sets):
        """🎯 Selecciona el mejor conjunto ESTABLE"""
        usable_sets = [s for s in available_sets.values() if s["usable"]]
        
        if not usable_sets:
            return None
        
        # Priorizar CORE_BODY (hombros + caderas) por estabilidad
        core_set = next((s for s in usable_sets if s["name"] == "CORE_BODY"), None)
        if core_set and core_set["quality_score"] > 0.8:
            return core_set
        
        # Si no, el mejor disponible
        return max(usable_sets, key=lambda s: s["quality_score"])
    
    def _calculate_stable_orientation_metrics(self, landmarks, landmark_set):
        """
        📐 MÉTRICAS SIMPLIFICADAS Y REALISTAS
        🚫 Sin cálculos exóticos que generan ratios gigantes
        """
        metrics = {}
        landmark_ids = landmark_set["landmarks"]
        
        # 🎯 PRIORIDAD 1: CADERAS (más estable)
        if 23 in landmark_ids and 24 in landmark_ids:
            l_hip, r_hip = landmarks[23], landmarks[24]
            hip_width = abs(l_hip.x - r_hip.x)
            
            # 🆕 LÓGICA SIMPLE Y DIRECTA
            if hip_width > 0.18:      # Muy separadas = FRONTAL claro
                combined_ratio = 2.2
            elif hip_width > 0.12:    # Moderadamente separadas = FRONTAL
                combined_ratio = 1.9  
            elif hip_width > 0.07:    # Poco separadas = DIAGONAL
                combined_ratio = 1.4
            else:                     # Muy juntas = SAGITAL
                combined_ratio = 0.9
            
            metrics.update({
                "hip_width": hip_width,
                "combined_ratio": combined_ratio,
                "primary_metric": "HIPS",
                "analysis_type": "HIP_BASED"
            })
        
        # 🎯 PRIORIDAD 2: HOMBROS (si caderas no disponibles)
        elif 11 in landmark_ids and 12 in landmark_ids:
            l_shoulder, r_shoulder = landmarks[11], landmarks[12]
            shoulder_width = abs(l_shoulder.x - r_shoulder.x)
            shoulder_height_diff = abs(l_shoulder.y - r_shoulder.y)
            
            # ⚠️ RECHAZAR si hay movimiento de brazos obvio
            if shoulder_height_diff > 0.08:  # Hombros muy desnivelados
                metrics.update({
                    "combined_ratio": 1.4,  # Forzar DIAGONAL hasta que se estabilice
                    "primary_metric": "MOVEMENT_DETECTED",
                    "analysis_type": "MOVEMENT_DETECTED"
                })
            else:
                # Usar lógica similar a caderas
                if shoulder_width > 0.20:
                    combined_ratio = 2.1
                elif shoulder_width > 0.14:
                    combined_ratio = 1.8
                elif shoulder_width > 0.08:
                    combined_ratio = 1.3
                else:
                    combined_ratio = 0.8
                
                metrics.update({
                    "shoulder_width": shoulder_width,
                    "combined_ratio": combined_ratio,
                    "primary_metric": "SHOULDERS",
                    "analysis_type": "SHOULDER_BASED"
                })
        
        # 🎯 FALLBACK: Un solo hombro
        elif 11 in landmark_ids or 12 in landmark_ids:
            visible_shoulder = landmarks[11] if 11 in landmark_ids else landmarks[12]
            centrality = abs(visible_shoulder.x - 0.5)
            
            if centrality < 0.15:      # Muy centrado = SAGITAL
                combined_ratio = 0.9
            elif centrality < 0.25:    # Moderadamente centrado = DIAGONAL  
                combined_ratio = 1.3
            else:                      # No centrado = FRONTAL parcial
                combined_ratio = 1.7
            
            metrics.update({
                "centrality": centrality,
                "combined_ratio": combined_ratio,
                "primary_metric": "SINGLE_SHOULDER",
                "analysis_type": "UNILATERAL"
            })
        
        else:
            # Sin datos suficientes
            metrics.update({
                "combined_ratio": 0,
                "primary_metric": "NONE",
                "analysis_type": "INSUFFICIENT"
            })
        
        return metrics
    
    def _classify_stable_orientation(self, metrics):
        """
        🎯 CLASIFICACIÓN CORREGIDA - ARREGLA LA LÓGICA ROTA
        """
        primary_ratio = metrics.get("combined_ratio", 0)
        analysis_type = metrics.get("analysis_type", "UNKNOWN")
        
        if primary_ratio == 0:
            return {"orientation": "UNKNOWN", "confidence": 0.0}
        
        thresholds = self.orientation_thresholds
        
        # 🆕 LÓGICA CORREGIDA - Usar analysis_type REAL
        if analysis_type in ["HIP_BASED", "SHOULDER_BASED"]:  # ← CORREGIDO
            
            # Clasificación por ratio (como debería ser)
            if primary_ratio >= thresholds["FRONTAL_STRONG"]:
                orientation = "FRONTAL"
                confidence = 0.9
                
            elif primary_ratio >= thresholds["FRONTAL_WEAK"]:
                orientation = "FRONTAL" 
                confidence = 0.8
                
            elif primary_ratio <= thresholds["SAGITAL_STRONG"]:
                orientation = "SAGITAL"
                confidence = 0.9
                
            elif primary_ratio <= thresholds["SAGITAL_EXTENDED"]:
                orientation = "SAGITAL"
                confidence = 0.8
                
            elif thresholds["DIAGONAL_ZONE"][0] <= primary_ratio <= thresholds["DIAGONAL_ZONE"][1]:
                orientation = "DIAGONAL"
                confidence = 0.7
                
            else:
                # 🆕 FUERA DE RANGOS ESPERADOS - Forzar clasificación
                if primary_ratio > 2.2:
                    orientation = "FRONTAL"
                    confidence = 0.7
                elif primary_ratio < 0.8:
                    orientation = "SAGITAL" 
                    confidence = 0.7
                else:
                    orientation = "DIAGONAL"
                    confidence = 0.6
                
        elif analysis_type == "MOVEMENT_DETECTED":
            # Durante movimiento, mantener DIAGONAL
            orientation = "DIAGONAL"
            confidence = 0.5
            
        elif analysis_type == "UNILATERAL":
            # Casos de un solo hombro
            centrality = metrics.get("centrality", 0.5)
            
            if centrality < 0.15:  # Muy centrado
                orientation = "SAGITAL"
                confidence = 0.8
            elif centrality > 0.3:  # Muy descentrado
                orientation = "FRONTAL"
                confidence = 0.7
            else:
                orientation = "DIAGONAL"
                confidence = 0.6
            
        else:
            # Fallback
            orientation = "DIAGONAL"
            confidence = 0.4
        
        return {
            "orientation": orientation,
            "confidence": confidence,
            "primary_ratio": primary_ratio,
            "analysis_type": analysis_type
        }
    
    def _classify_with_transitions(self, metrics):
        """🔄 Clasificación con transiciones suaves"""
        
        primary_ratio = metrics.get("combined_ratio", 0)
        
        if primary_ratio >= self.thresholds["FRONTAL_WEAK"]:
            return "FRONTAL", self._calculate_confidence(primary_ratio, "FRONTAL")
            
        elif primary_ratio <= self.thresholds["SAGITAL_EXTENDED"]:
            # 🎯 Sagital extendido - permite análisis con lado dominante visible
            if primary_ratio <= self.thresholds["SAGITAL_STRONG"]:
                return "SAGITAL_PURE", 0.9  # Sagital puro
            else:
                return "SAGITAL_EXTENDED", 0.7  # Sagital con lado visible
                
        else:
            # Zona diagonal - mantener última orientación estable
            return self._maintain_stable_orientation(), 0.5
    
    def _apply_strong_orientation_filter(self, orientation_result):
        """
        🔄 FILTRO TEMPORAL ULTRA FUERTE - NO cambia por movimientos de brazos
        """
        # Agregar a historial
        self.orientation_history.append(orientation_result)
        
        # Mantener MÁS historia
        if len(self.orientation_history) > 20:  # 🆕 Aumentar de 15 a 20
            self.orientation_history.pop(0)
        
        # Requerir MÁS muestras para cambios
        if len(self.orientation_history) < 8:  # 🆕 Aumentar de 5 a 8
            return orientation_result
        
        # Análisis de tendencias MÁS conservador
        recent_orientations = self.orientation_history[-12:]  # 🆕 Últimas 12 muestras
        orientation_weights = {}
        
        for result in recent_orientations:
            orientation = result["orientation"]
            confidence = result["confidence"]
            
            if orientation not in orientation_weights:
                orientation_weights[orientation] = 0
            orientation_weights[orientation] += confidence
        
        if orientation_weights:
            best_orientation = max(orientation_weights, key=orientation_weights.get)
            best_weight = orientation_weights[best_orientation]
            current_weight = orientation_weights.get(orientation_result["orientation"], 0)
            
            # Requerir diferencia MUY SIGNIFICATIVA para cambiar
            weight_difference = abs(best_weight - current_weight)
            
            if weight_difference < 2.0:  # 🆕 Aumentar de 1.0 a 2.0
                return orientation_result  # Mantener actual
            else:
                # 🎯 VERIFICACIÓN ADICIONAL: Rechazar cambios durante movimiento
                current_analysis_type = orientation_result.get("analysis_type", "")
                
                if current_analysis_type == "MOVEMENT_DETECTED":
                    # NO cambiar orientación durante movimientos detectados
                    return self.orientation_history[-2] if len(self.orientation_history) >= 2 else orientation_result
                
                # Cambiar solo con evidencia MUY fuerte
                return {
                    "orientation": best_orientation,
                    "confidence": min(orientation_result["confidence"], best_weight / len(recent_orientations)),
                    "primary_ratio": orientation_result["primary_ratio"],
                    "analysis_type": orientation_result["analysis_type"]
                }
        
        return orientation_result
    
    def _insufficient_orientation_data(self):
        return {
            "orientation": "INSUFFICIENT_DATA",
            "confidence": 0.0,
            "landmark_set_used": "NONE",
            "landmark_count": 0
        }
    
    def _error_response(self, error_msg):
        return {
            "orientation": "ERROR",
            "confidence": 0.0,
            "landmark_set_used": "ERROR",
            "landmark_count": 0,
            "error": error_msg
        }