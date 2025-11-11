"""
ANGLE DEBUGGER - Sistema de debugging exhaustivo para validación de ángulos
SOLO PARA ADMINISTRADOR - Comparar cálculos con goniómetro

Basado en goniometría estándar (Norkin & White, Magee)
Todos los segmentos se miden entre SEGMENTOS CORPORALES, no contra eje vertical fijo
"""

import cv2
import numpy as np
import json
import os
from datetime import datetime

class AngleDebugger:
    """Sistema de debugging para validación de ángulos biomecánicos"""
    
    def __init__(self, output_dir='debug_angles'):
        self.output_dir = output_dir
        self.enabled = False
        self.capture_count = 0
        
        # Crear directorio de salida
        os.makedirs(output_dir, exist_ok=True)
        
    def enable(self):
        """Activar debugging"""
        self.enabled = True
        print("DEBUG ACTIVADO - Solo visible para administrador")
        
    def disable(self):
        """Desactivar debugging"""
        self.enabled = False
        print("DEBUG DESACTIVADO")
        
    def debug_angle_calculation(self, frame, landmarks, segment, exercise, side='right'):
        """
        Debug completo de cálculo de ángulo
        
        Args:
            frame: Frame de video
            landmarks: MediaPipe landmarks
            segment: 'shoulder', 'elbow', 'hip', 'knee', 'ankle'
            exercise: 'flexion', 'abduction', etc.
            side: 'right' o 'left'
        
        Returns:
            dict con frame debuggeado y datos completos
        """
        if not self.enabled:
            return None
        
        # Delegar a método específico por segmento
        if segment == 'shoulder':
            return self._debug_shoulder(frame, landmarks, exercise, side)
        elif segment == 'elbow':
            return self._debug_elbow(frame, landmarks, side)
        elif segment == 'hip':
            return self._debug_hip(frame, landmarks, exercise, side)
        elif segment == 'knee':
            return self._debug_knee(frame, landmarks, side)
        elif segment == 'ankle':
            return self._debug_ankle(frame, landmarks, side)
        else:
            return None
    
    def _debug_shoulder(self, frame, landmarks, exercise, side):
        """Debug de ángulo de hombro"""
        try:
            # Seleccionar puntos según lado
            if side == 'right':
                hip = landmarks[24]
                shoulder = landmarks[12]
                elbow = landmarks[14]
                side_label = "DERECHO"
                color = (0, 255, 0)  # Verde
            else:
                hip = landmarks[23]
                shoulder = landmarks[11]
                elbow = landmarks[13]
                side_label = "IZQUIERDO"
                color = (255, 0, 0)  # Azul
            
            # Verificar visibilidad
            if hip.visibility < 0.5 or shoulder.visibility < 0.5 or elbow.visibility < 0.5:
                return {
                    'error': 'Puntos poco visibles',
                    'visibilities': {
                        'hip': hip.visibility,
                        'shoulder': shoulder.visibility,
                        'elbow': elbow.visibility
                    }
                }
            
            # Construir vectores (GONIOMETRÍA ESTÁNDAR)
            # Vector 1: TRONCO (cadera → hombro) - Brazo fijo del goniómetro
            v1 = np.array([
                shoulder.x - hip.x,
                shoulder.y - hip.y,
                shoulder.z - hip.z
            ])
            
            # Vector 2: BRAZO (hombro → codo) - Brazo móvil del goniómetro
            v2 = np.array([
                elbow.x - shoulder.x,
                elbow.y - shoulder.y,
                elbow.z - shoulder.z
            ])
            
            # Cálculo del ángulo
            dot_product = np.dot(v1, v2)
            magnitude_v1 = np.linalg.norm(v1)
            magnitude_v2 = np.linalg.norm(v2)
            
            if magnitude_v1 == 0 or magnitude_v2 == 0:
                return {'error': 'Vector con magnitud cero'}
            
            cos_angle = dot_product / (magnitude_v1 * magnitude_v2)
            cos_angle_clamped = np.clip(cos_angle, -1.0, 1.0)
            angle_rad = np.arccos(cos_angle_clamped)
            angle_deg = np.degrees(angle_rad)
            
            # Construir datos de debugging
            debug_data = {
                'timestamp': datetime.now().isoformat(),
                'segment': 'HOMBRO',
                'exercise': exercise,
                'side': side_label,
                'goniometry_reference': 'Norkin & White - Brazo fijo: TRONCO, Brazo móvil: HUMERO',
                'coordinates': {
                    'hip': {'x': float(hip.x), 'y': float(hip.y), 'z': float(hip.z), 'vis': float(hip.visibility)},
                    'shoulder': {'x': float(shoulder.x), 'y': float(shoulder.y), 'z': float(shoulder.z), 'vis': float(shoulder.visibility)},
                    'elbow': {'x': float(elbow.x), 'y': float(elbow.y), 'z': float(elbow.z), 'vis': float(elbow.visibility)}
                },
                'vectors': {
                    'v1_tronco': {'x': float(v1[0]), 'y': float(v1[1]), 'z': float(v1[2])},
                    'v2_brazo': {'x': float(v2[0]), 'y': float(v2[1]), 'z': float(v2[2])}
                },
                'calculations': {
                    'dot_product': float(dot_product),
                    'magnitude_v1': float(magnitude_v1),
                    'magnitude_v2': float(magnitude_v2),
                    'cos_angle': float(cos_angle),
                    'cos_angle_clamped': float(cos_angle_clamped),
                    'angle_radians': float(angle_rad),
                    'angle_degrees': float(angle_deg)
                },
                'final_angle': float(angle_deg)
            }
            
            # Dibujar en frame
            frame_debug = self._draw_debug_overlay(
                frame, landmarks, debug_data, side, 
                point_indices={'proximal': 24 if side == 'right' else 23, 
                              'joint': 12 if side == 'right' else 11,
                              'distal': 14 if side == 'right' else 13},
                color=color
            )
            
            return {
                'frame': frame_debug,
                'data': debug_data
            }
            
        except Exception as e:
            print(f"Error en _debug_shoulder: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _debug_elbow(self, frame, landmarks, side):
        """Debug de ángulo de codo"""
        try:
            # Seleccionar puntos según lado
            if side == 'right':
                shoulder = landmarks[12]
                elbow = landmarks[14]
                wrist = landmarks[16]
                side_label = "DERECHO"
                color = (0, 255, 0)
            else:
                shoulder = landmarks[11]
                elbow = landmarks[13]
                wrist = landmarks[15]
                side_label = "IZQUIERDO"
                color = (255, 0, 0)
            
            # Verificar visibilidad
            if shoulder.visibility < 0.5 or elbow.visibility < 0.5 or wrist.visibility < 0.5:
                return {'error': 'Puntos poco visibles'}
            
            # Construir vectores (GONIOMETRÍA ESTÁNDAR)
            # Vector 1: BRAZO SUPERIOR (hombro → codo) - Brazo fijo
            v1 = np.array([
                elbow.x - shoulder.x,
                elbow.y - shoulder.y,
                elbow.z - shoulder.z
            ])
            
            # Vector 2: ANTEBRAZO (codo → muñeca) - Brazo móvil
            v2 = np.array([
                wrist.x - elbow.x,
                wrist.y - elbow.y,
                wrist.z - elbow.z
            ])
            
            # Cálculo del ángulo
            dot_product = np.dot(v1, v2)
            magnitude_v1 = np.linalg.norm(v1)
            magnitude_v2 = np.linalg.norm(v2)
            
            if magnitude_v1 == 0 or magnitude_v2 == 0:
                return {'error': 'Vector con magnitud cero'}
            
            cos_angle = dot_product / (magnitude_v1 * magnitude_v2)
            cos_angle_clamped = np.clip(cos_angle, -1.0, 1.0)
            angle_rad = np.arccos(cos_angle_clamped)
            angle_deg = np.degrees(angle_rad)
            
            debug_data = {
                'timestamp': datetime.now().isoformat(),
                'segment': 'CODO',
                'exercise': 'flexion',
                'side': side_label,
                'goniometry_reference': 'Norkin & White - Brazo fijo: HUMERO, Brazo móvil: RADIO',
                'coordinates': {
                    'shoulder': {'x': float(shoulder.x), 'y': float(shoulder.y), 'z': float(shoulder.z), 'vis': float(shoulder.visibility)},
                    'elbow': {'x': float(elbow.x), 'y': float(elbow.y), 'z': float(elbow.z), 'vis': float(elbow.visibility)},
                    'wrist': {'x': float(wrist.x), 'y': float(wrist.y), 'z': float(wrist.z), 'vis': float(wrist.visibility)}
                },
                'vectors': {
                    'v1_brazo_superior': {'x': float(v1[0]), 'y': float(v1[1]), 'z': float(v1[2])},
                    'v2_antebrazo': {'x': float(v2[0]), 'y': float(v2[1]), 'z': float(v2[2])}
                },
                'calculations': {
                    'dot_product': float(dot_product),
                    'magnitude_v1': float(magnitude_v1),
                    'magnitude_v2': float(magnitude_v2),
                    'cos_angle': float(cos_angle),
                    'angle_degrees': float(angle_deg)
                },
                'final_angle': float(angle_deg)
            }
            
            frame_debug = self._draw_debug_overlay(
                frame, landmarks, debug_data, side,
                point_indices={'proximal': 12 if side == 'right' else 11,
                              'joint': 14 if side == 'right' else 13,
                              'distal': 16 if side == 'right' else 15},
                color=color
            )
            
            return {'frame': frame_debug, 'data': debug_data}
            
        except Exception as e:
            print(f"Error en _debug_elbow: {e}")
            return None
    
    def _debug_hip(self, frame, landmarks, exercise, side):
        """Debug de ángulo de cadera"""
        try:
            if side == 'right':
                shoulder = landmarks[12]
                hip = landmarks[24]
                knee = landmarks[26]
                side_label = "DERECHO"
                color = (0, 255, 0)
            else:
                shoulder = landmarks[11]
                hip = landmarks[23]
                knee = landmarks[25]
                side_label = "IZQUIERDO"
                color = (255, 0, 0)
            
            if shoulder.visibility < 0.5 or hip.visibility < 0.5 or knee.visibility < 0.5:
                return {'error': 'Puntos poco visibles'}
            
            # Vector 1: TRONCO (hombro → cadera)
            v1 = np.array([
                hip.x - shoulder.x,
                hip.y - shoulder.y,
                hip.z - shoulder.z
            ])
            
            # Vector 2: MUSLO (cadera → rodilla)
            v2 = np.array([
                knee.x - hip.x,
                knee.y - hip.y,
                knee.z - hip.z
            ])
            
            dot_product = np.dot(v1, v2)
            magnitude_v1 = np.linalg.norm(v1)
            magnitude_v2 = np.linalg.norm(v2)
            
            if magnitude_v1 == 0 or magnitude_v2 == 0:
                return {'error': 'Vector con magnitud cero'}
            
            cos_angle = dot_product / (magnitude_v1 * magnitude_v2)
            cos_angle_clamped = np.clip(cos_angle, -1.0, 1.0)
            angle_rad = np.arccos(cos_angle_clamped)
            angle_deg = np.degrees(angle_rad)
            
            debug_data = {
                'timestamp': datetime.now().isoformat(),
                'segment': 'CADERA',
                'exercise': exercise,
                'side': side_label,
                'goniometry_reference': 'Norkin & White - Brazo fijo: TRONCO, Brazo móvil: FEMUR',
                'final_angle': float(angle_deg)
            }
            
            frame_debug = self._draw_debug_overlay(
                frame, landmarks, debug_data, side,
                point_indices={'proximal': 12 if side == 'right' else 11,
                              'joint': 24 if side == 'right' else 23,
                              'distal': 26 if side == 'right' else 25},
                color=color
            )
            
            return {'frame': frame_debug, 'data': debug_data}
            
        except Exception as e:
            return None
    
    def _debug_knee(self, frame, landmarks, side):
        """Debug de ángulo de rodilla"""
        try:
            if side == 'right':
                hip = landmarks[24]
                knee = landmarks[26]
                ankle = landmarks[28]
                side_label = "DERECHO"
                color = (0, 255, 0)
            else:
                hip = landmarks[23]
                knee = landmarks[25]
                ankle = landmarks[27]
                side_label = "IZQUIERDO"
                color = (255, 0, 0)
            
            if hip.visibility < 0.5 or knee.visibility < 0.5 or ankle.visibility < 0.5:
                return {'error': 'Puntos poco visibles'}
            
            # Vector 1: MUSLO (cadera → rodilla)
            v1 = np.array([
                knee.x - hip.x,
                knee.y - hip.y,
                knee.z - hip.z
            ])
            
            # Vector 2: PIERNA (rodilla → tobillo)
            v2 = np.array([
                ankle.x - knee.x,
                ankle.y - knee.y,
                ankle.z - knee.z
            ])
            
            dot_product = np.dot(v1, v2)
            magnitude_v1 = np.linalg.norm(v1)
            magnitude_v2 = np.linalg.norm(v2)
            
            if magnitude_v1 == 0 or magnitude_v2 == 0:
                return {'error': 'Vector con magnitud cero'}
            
            cos_angle = dot_product / (magnitude_v1 * magnitude_v2)
            cos_angle_clamped = np.clip(cos_angle, -1.0, 1.0)
            angle_rad = np.arccos(cos_angle_clamped)
            angle_deg = np.degrees(angle_rad)
            
            debug_data = {
                'timestamp': datetime.now().isoformat(),
                'segment': 'RODILLA',
                'exercise': 'flexion',
                'side': side_label,
                'goniometry_reference': 'Norkin & White - Brazo fijo: FEMUR, Brazo móvil: TIBIA',
                'final_angle': float(angle_deg)
            }
            
            frame_debug = self._draw_debug_overlay(
                frame, landmarks, debug_data, side,
                point_indices={'proximal': 24 if side == 'right' else 23,
                              'joint': 26 if side == 'right' else 25,
                              'distal': 28 if side == 'right' else 27},
                color=color
            )
            
            return {'frame': frame_debug, 'data': debug_data}
            
        except Exception as e:
            return None
    
    def _debug_ankle(self, frame, landmarks, side):
        """Debug de ángulo de tobillo"""
        try:
            if side == 'right':
                knee = landmarks[26]
                ankle = landmarks[28]
                foot = landmarks[32]  # Punta del pie
                side_label = "DERECHO"
                color = (0, 255, 0)
            else:
                knee = landmarks[25]
                ankle = landmarks[27]
                foot = landmarks[31]
                side_label = "IZQUIERDO"
                color = (255, 0, 0)
            
            if knee.visibility < 0.5 or ankle.visibility < 0.5 or foot.visibility < 0.5:
                return {'error': 'Puntos poco visibles'}
            
            # Vector 1: PIERNA (rodilla → tobillo)
            v1 = np.array([
                ankle.x - knee.x,
                ankle.y - knee.y,
                ankle.z - knee.z
            ])
            
            # Vector 2: PIE (tobillo → punta del pie)
            v2 = np.array([
                foot.x - ankle.x,
                foot.y - ankle.y,
                foot.z - ankle.z
            ])
            
            dot_product = np.dot(v1, v2)
            magnitude_v1 = np.linalg.norm(v1)
            magnitude_v2 = np.linalg.norm(v2)
            
            if magnitude_v1 == 0 or magnitude_v2 == 0:
                return {'error': 'Vector con magnitud cero'}
            
            cos_angle = dot_product / (magnitude_v1 * magnitude_v2)
            cos_angle_clamped = np.clip(cos_angle, -1.0, 1.0)
            angle_rad = np.arccos(cos_angle_clamped)
            angle_deg = np.degrees(angle_rad)
            
            debug_data = {
                'timestamp': datetime.now().isoformat(),
                'segment': 'TOBILLO',
                'exercise': 'dorsiflexion',
                'side': side_label,
                'goniometry_reference': 'Norkin & White - Brazo fijo: TIBIA, Brazo móvil: 5to METATARSIANO',
                'final_angle': float(angle_deg)
            }
            
            frame_debug = self._draw_debug_overlay(
                frame, landmarks, debug_data, side,
                point_indices={'proximal': 26 if side == 'right' else 25,
                              'joint': 28 if side == 'right' else 27,
                              'distal': 32 if side == 'right' else 31},
                color=color
            )
            
            return {'frame': frame_debug, 'data': debug_data}
            
        except Exception as e:
            return None
    
    def _draw_debug_overlay(self, frame, landmarks, debug_data, side, point_indices, color):
        """Dibujar overlay de debugging en frame"""
        h, w, _ = frame.shape
        frame_debug = frame.copy()
        
        # Obtener puntos
        prox = landmarks[point_indices['proximal']]
        joint = landmarks[point_indices['joint']]
        dist = landmarks[point_indices['distal']]
        
        # Convertir a coordenadas de píxeles
        prox_pt = (int(prox.x * w), int(prox.y * h))
        joint_pt = (int(joint.x * w), int(joint.y * h))
        dist_pt = (int(dist.x * w), int(dist.y * h))
        
        # Dibujar puntos
        cv2.circle(frame_debug, prox_pt, 8, (0, 0, 255), -1)  # Rojo
        cv2.circle(frame_debug, joint_pt, 8, (255, 255, 0), -1)  # Cyan
        cv2.circle(frame_debug, dist_pt, 8, (255, 0, 255), -1)  # Magenta
        
        # Dibujar vectores
        cv2.line(frame_debug, prox_pt, joint_pt, (0, 255, 255), 4)  # Vector 1 (amarillo)
        cv2.line(frame_debug, joint_pt, dist_pt, (255, 128, 0), 4)  # Vector 2 (naranja)
        
        # Ángulo
        angle = debug_data['final_angle']
        angle_text = f"ANGULO: {angle:.1f} deg"
        
        # Fondo negro
        text_size = cv2.getTextSize(angle_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)[0]
        cv2.rectangle(frame_debug, (10, h - 60), (10 + text_size[0] + 20, h - 10), (0, 0, 0), -1)
        cv2.putText(frame_debug, angle_text, (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        
        # Info del segmento
        info_text = f"{debug_data['segment']} {debug_data['side']}"
        cv2.putText(frame_debug, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        return frame_debug
    
    def capture_debug_snapshot(self, frame, debug_data, manual_angle=None):
        """Guardar frame de debugging con datos JSON"""
        if not self.enabled:
            return {'success': False, 'message': 'Debug no activo'}
        
        self.capture_count += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"debug_{timestamp}_{self.capture_count:03d}"
        
        # Guardar imagen
        img_path = os.path.join(self.output_dir, f"{base_name}.jpg")
        cv2.imwrite(img_path, frame)
        
        # Agregar ángulo manual si se proporciona
        if manual_angle is not None:
            debug_data['manual_measurement'] = {
                'angle': manual_angle,
                'difference': abs(debug_data['final_angle'] - manual_angle),
                'percentage_error': abs(debug_data['final_angle'] - manual_angle) / manual_angle * 100 if manual_angle != 0 else 0
            }
        
        # Guardar JSON
        json_path = os.path.join(self.output_dir, f"{base_name}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
        
        print(f"SNAPSHOT GUARDADO: {base_name}")
        print(f"  Angulo calculado: {debug_data['final_angle']:.1f} grados")
        if manual_angle:
            print(f"  Angulo manual: {manual_angle:.1f} grados")
            print(f"  Diferencia: {debug_data['manual_measurement']['difference']:.1f} grados")
        
        return {
            'success': True,
            'message': f'Snapshot guardado: {base_name}',
            'path': img_path
        }

# Instancia global
angle_debugger = AngleDebugger()
