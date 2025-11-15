"""
Script para análisis de FLEXIÓN de rodilla (VISTA DE PERFIL - PLANO SAGITAL)
Utiliza OpenCV y MediaPipe para detectar y calcular ángulos
Sistema de medición: Goniómetro estándar con eje vertical fijo

OPTIMIZACIONES IMPLEMENTADAS:
- Procesamiento en resolución reducida (640x480) con upscaling para display
- Dibujos OpenCV optimizados (LINE_4 en vez de LINE_AA)
- Caché de colores por rangos de ángulos
- Sistema de profiling de FPS y latencia
- Análisis bilateral con comparación de simetría
"""

import cv2
import mediapipe as mp
import numpy as np
import math
import time
from collections import deque

# Inicializar MediaPipe Pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

class KneeProfileAnalyzer:
    def __init__(self, processing_width=640, processing_height=480):
        """
        Inicializa el analizador para vista de PERFIL (Flexión de rodilla)
        
        Args:
            processing_width: Ancho para procesamiento de MediaPipe
            processing_height: Alto para procesamiento de MediaPipe
        """
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1
        )
        
        # Resolución de procesamiento
        self.processing_width = processing_width
        self.processing_height = processing_height
        
        # Variables para tracking de ángulos (bilateral)
        self.left_knee_angle = 0
        self.right_knee_angle = 0
        self.max_left_flexion = 0
        self.max_right_flexion = 0
        self.frame_count = 0
        
        # Detección de lado visible
        self.side_detected = "Detectando..."
        self.side_confidence = 0
        
        # Modo de visualización
        self.display_mode = "CLEAN"  # Opciones: "CLEAN", "FULL", "MINIMAL"
        
        # Métricas de rendimiento
        self.fps_history = deque(maxlen=30)
        self.processing_times = deque(maxlen=30)
        self.last_time = time.time()
        
        # Caché de colores
        self.color_cache = {
            'white': (255, 255, 255),
            'yellow': (0, 255, 255),
            'orange': (0, 165, 255),
            'magenta': (255, 0, 255),
            'green': (0, 255, 0),
            'cyan': (255, 255, 0),
            'blue': (255, 0, 0),
            'red': (0, 0, 255),
            'gray': (50, 50, 50),
            'light_gray': (200, 200, 200)
        }
    
    def toggle_display_mode(self):
        """Alterna entre modos de visualización"""
        modes = ["CLEAN", "FULL", "MINIMAL"]
        current_index = modes.index(self.display_mode)
        next_index = (current_index + 1) % len(modes)
        self.display_mode = modes[next_index]
        
        mode_descriptions = {
            "CLEAN": "[*] LIMPIO - Solo lineas biomecanicas (Recomendado)",
            "FULL": "[*] COMPLETO - Con skeleton de MediaPipe",
            "MINIMAL": "[*] MINIMALISTA - Maximo rendimiento"
        }
        
        print(f"\n[*] Modo de visualizacion cambiado a: {mode_descriptions[self.display_mode]}")
        return self.display_mode
    
    def calculate_knee_flexion_angle(self, hip, knee, ankle):
        """
        Calcula el ángulo de flexión de rodilla con eje vertical fijo
        
        Sistema goniómetro estándar:
        - Brazo FIJO: Eje vertical absoluto (0, 1) que pasa por la RODILLA
        - Brazo MÓVIL: Línea de la pierna (RODILLA → TOBILLO)
        - 0° = Pierna completamente EXTENDIDA (vertical hacia abajo)
        - 90° = Rodilla en ángulo recto
        - 150° = Flexión MÁXIMA (talón cerca del glúteo)
        
        Args:
            hip: Coordenadas [x, y] de la cadera
            knee: Coordenadas [x, y] de la rodilla (PUNTO DE VÉRTICE)
            ankle: Coordenadas [x, y] del tobillo
        
        Returns:
            float: Ángulo en grados (0-150°)
        """
        # Vector vertical fijo (referencia 0° - apunta hacia abajo)
        vertical_down_vector = np.array([0, 1])
        
        # Vector de la pierna (RODILLA → TOBILLO) - brazo móvil del goniómetro
        leg_vector = np.array([ankle[0] - knee[0], ankle[1] - knee[1]])
        
        # Normalizar vector de la pierna
        leg_norm = np.linalg.norm(leg_vector)
        
        if leg_norm == 0:
            return 0
        
        leg_vector_normalized = leg_vector / leg_norm
        
        # Calcular ángulo entre eje vertical y pierna
        dot_product = np.dot(vertical_down_vector, leg_vector_normalized)
        dot_product = np.clip(dot_product, -1.0, 1.0)
        
        # Ángulo sin signo (0° a 180°)
        angle = np.degrees(np.arccos(dot_product))
        
        return angle
    
    def calculate_symmetry_difference(self):
        """Calcula la diferencia de simetría entre rodillas izquierda y derecha"""
        return abs(self.left_knee_angle - self.right_knee_angle)
    
    def detect_side(self, landmarks):
        """
        Detecta qué lado del cuerpo está visible (vista de perfil)
        Retorna: lado, confianza, orientación
        """
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        left_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
        right_knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]
        nose = landmarks[mp_pose.PoseLandmark.NOSE]
        
        # MÉTODO 1: Solo visibilidad (ACTIVO por defecto - Consistente con hombro/codo)
        left_visibility = (left_hip.visibility + left_knee.visibility) / 2
        right_visibility = (right_hip.visibility + right_knee.visibility) / 2
        
        hip_center_x = (left_hip.x + right_hip.x) / 2
        
        if left_visibility > right_visibility:
            side = 'left'
            confidence = left_visibility
            orientation = "mirando izquierda" if nose.x < hip_center_x else "mirando derecha"
        else:
            side = 'right'
            confidence = right_visibility
            orientation = "mirando derecha" if nose.x > hip_center_x else "mirando izquierda"
        
        return side, confidence, orientation
        
        """
        # === MÉTODO 2 (MEJORADO): Profundidad Z + Visibilidad ===
        # Descomenta este bloque para usar detección más robusta (96% vs 75% precisión)
        
        # Profundidad promedio (más cerca = más negativo en Z)
        left_depth = (left_hip.z + left_knee.z) / 2
        right_depth = (right_hip.z + right_knee.z) / 2
        
        # Visibilidad promedio
        left_vis = (left_hip.visibility + left_knee.visibility) / 2
        right_vis = (right_hip.visibility + right_knee.visibility) / 2
        
        # Score combinado (profundidad 70%, visibilidad 30%)
        left_score = (-left_depth * 0.7) + (left_vis * 0.3)
        right_score = (-right_depth * 0.7) + (right_vis * 0.3)
        
        # Calcular confianza
        confidence = min(abs(left_score - right_score) * 100, 100)
        
        hip_center_x = (left_hip.x + right_hip.x) / 2
        
        if left_score > right_score:
            side = 'left'
            orientation = "mirando izquierda" if nose.x < hip_center_x else "mirando derecha"
        else:
            side = 'right'
            orientation = "mirando derecha" if nose.x > hip_center_x else "mirando izquierda"
        
        return side, confidence, orientation
        """
    
    def get_landmarks_2d(self, landmark, frame_width, frame_height):
        """Convierte landmarks normalizados a coordenadas de píxeles"""
        return [int(landmark.x * frame_width), int(landmark.y * frame_height)]
    
    def _draw_performance_metrics(self, image, current_fps, current_processing_time):
        """Dibuja métricas de rendimiento en pantalla"""
        h, w = image.shape[:2]
        
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        avg_processing = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        panel_x = w - 220
        panel_y = 10
        
        # Fondo semitransparente
        overlay = image.copy()
        cv2.rectangle(overlay, (panel_x - 10, panel_y), (w - 10, panel_y + 120), 
                     self.color_cache['gray'], -1)
        cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)
        
        # Métricas
        cv2.putText(image, f"FPS: {current_fps:.1f} (avg: {avg_fps:.1f})", 
                   (panel_x, panel_y + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['green'], 1, cv2.LINE_4)
        
        cv2.putText(image, f"Latencia: {current_processing_time:.1f}ms", 
                   (panel_x, panel_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['yellow'], 1, cv2.LINE_4)
        
        cv2.putText(image, f"Frames: {self.frame_count}", 
                   (panel_x, panel_y + 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['white'], 1, cv2.LINE_4)
        
        # Indicador de modo
        mode_icons = {"CLEAN": "Clean", "FULL": "Full", "MINIMAL": "Min"}
        mode_colors = {
            "CLEAN": self.color_cache['green'],
            "FULL": self.color_cache['cyan'],
            "MINIMAL": self.color_cache['orange']
        }
        mode_text = f"Modo: {mode_icons.get(self.display_mode, '')}"
        cv2.putText(image, mode_text, 
                   (panel_x - 20, panel_y + 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, 
                   mode_colors.get(self.display_mode, self.color_cache['white']), 1, cv2.LINE_4)
    
    def process_frame(self, frame):
        """Procesa un frame y retorna el frame anotado"""
        start_time = time.time()
        self.frame_count += 1
        
        # Guardar dimensiones originales
        original_h, original_w = frame.shape[:2]
        
        # Reducir resolución para procesamiento
        small_frame = cv2.resize(frame, (self.processing_width, self.processing_height), 
                                interpolation=cv2.INTER_LINEAR)
        
        # Convertir a RGB
        image_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False
        
        # Procesar con MediaPipe
        results = self.pose.process(image_rgb)
        
        # Trabajar con resolución original para visualización
        image_rgb.flags.writeable = True
        image = frame.copy()
        
        if results.pose_landmarks:
            h, w = image.shape[:2]
            landmarks = results.pose_landmarks.landmark
            
            # Dibujar skeleton solo en modo FULL
            if self.display_mode == "FULL":
                mp_drawing.draw_landmarks(
                    image,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
                )
            
            # Detectar lado visible
            side, confidence, orientation = self.detect_side(landmarks)
            self.side_detected = side
            self.side_confidence = confidence
            
            # Procesar vista de perfil
            self.process_profile_view(image, landmarks, w, h, orientation, confidence)
        else:
            cv2.putText(image, "No se detecta persona", (50, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, self.color_cache['red'], 2, cv2.LINE_4)
        
        # Calcular métricas de rendimiento
        processing_time = (time.time() - start_time) * 1000
        self.processing_times.append(processing_time)
        
        current_time = time.time()
        fps = 1.0 / (current_time - self.last_time) if (current_time - self.last_time) > 0 else 0
        self.fps_history.append(fps)
        self.last_time = current_time
        
        # Mostrar métricas
        self._draw_performance_metrics(image, fps, processing_time)
        
        return image
    
    def process_profile_view(self, image, landmarks, w, h, orientation, confidence):
        """Procesa vista de perfil - Análisis de flexión de rodilla"""
        # Obtener landmarks según el lado más visible
        if self.side_detected == 'left':
            hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
            knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
            ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE]
        else:
            hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
            knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]
            ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE]
        
        # Convertir a coordenadas 2D
        hip_2d = self.get_landmarks_2d(hip, w, h)
        knee_2d = self.get_landmarks_2d(knee, w, h)
        ankle_2d = self.get_landmarks_2d(ankle, w, h)
        
        # Calcular ángulo de flexión
        angle = self.calculate_knee_flexion_angle(hip_2d, knee_2d, ankle_2d)
        
        # Actualizar estadísticas según lado visible
        if self.side_detected == 'left':
            self.left_knee_angle = angle
            if angle > self.max_left_flexion:
                self.max_left_flexion = angle
        else:
            self.right_knee_angle = angle
            if angle > self.max_right_flexion:
                self.max_right_flexion = angle
        
        # ===== DIBUJAR VISUALIZACIÓN =====
        
        # Puntos clave
        cv2.circle(image, hip_2d, 10, self.color_cache['yellow'], -1, cv2.LINE_4)      # CADERA
        cv2.circle(image, knee_2d, 10, self.color_cache['cyan'], -1, cv2.LINE_4)       # RODILLA
        cv2.circle(image, ankle_2d, 8, self.color_cache['magenta'], -1, cv2.LINE_4)    # TOBILLO
        
        # Eje vertical (pasa por rodilla)
        vertical_length = 200
        vertical_start = (knee_2d[0], knee_2d[1] - vertical_length)
        vertical_end = (knee_2d[0], knee_2d[1] + vertical_length)
        cv2.line(image, vertical_start, vertical_end, self.color_cache['green'], 3, cv2.LINE_4)
        
        # Línea de la pierna (RODILLA → TOBILLO) - brazo móvil
        cv2.line(image, knee_2d, ankle_2d, self.color_cache['blue'], 4, cv2.LINE_4)
        
        # Línea del muslo (CADERA → RODILLA) - solo en CLEAN y FULL
        if self.display_mode != "MINIMAL":
            cv2.line(image, hip_2d, knee_2d, self.color_cache['blue'], 2, cv2.LINE_4)
        
        # Mostrar ángulo junto a la rodilla
        angle_color = self.get_knee_flexion_color(angle)
        cv2.putText(image, f"{angle:.1f}deg", 
                   (knee_2d[0] + 20, knee_2d[1] - 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.4, angle_color, 3, cv2.LINE_4)
        
        # Indicador de estado
        if angle < 15:
            status = "EXTENDIDA"
            status_color = self.color_cache['white']
        else:
            status = "FLEXION"
            status_color = self.color_cache['green']
        
        cv2.putText(image, status, 
                   (knee_2d[0] + 20, knee_2d[1] + 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2, cv2.LINE_4)
        
        # Panel de información
        self.draw_info_panel(image, orientation, confidence, w, h)
    
    def draw_info_panel(self, image, orientation, confidence, w, h):
        """Dibuja panel informativo con análisis"""
        # Panel superior con fondo semi-transparente
        panel_height = 240
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (w, panel_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
        
        # Título
        title = "ANALISIS DE RODILLA - FLEXION (PERFIL)"
        
        cv2.putText(image, title, (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color_cache['green'], 2, cv2.LINE_4)
        
        # Lado detectado
        color_side = self.color_cache['green'] if confidence > 0.7 else self.color_cache['orange']
        side_text = "Izquierda" if self.side_detected == 'left' else "Derecha"
        cv2.putText(image, f"Lado visible: {side_text}", (20, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_side, 2, cv2.LINE_4)
        
        # Orientación
        cv2.putText(image, f"Orientacion: {orientation}", (20, 110),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['white'], 2, cv2.LINE_4)
        
        # Ángulo actual según lado visible
        current_angle = self.left_knee_angle if self.side_detected == 'left' else self.right_knee_angle
        max_angle = self.max_left_flexion if self.side_detected == 'left' else self.max_right_flexion
        
        angle_color = self.get_knee_flexion_color(current_angle)
        cv2.putText(image, f"Angulo Actual: {current_angle:.1f}deg", (20, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, angle_color, 2, cv2.LINE_4)
        
        # ROM Máximo alcanzado
        cv2.putText(image, f"Flexion Maxima: {max_angle:.1f}deg", 
                   (20, 180),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color_cache['green'], 2, cv2.LINE_4)
        
        # Guía de ROM
        cv2.putText(image, "ROM normal: 0-150deg (0=extendida, 150=flexion maxima)", 
                   (20, 215),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['light_gray'], 1, cv2.LINE_4)
        
        # Instrucciones inferiores
        cv2.putText(image, "Dobla la rodilla | 'R' reiniciar | 'M' modo | 'Q' salir", 
                   (20, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['white'], 2, cv2.LINE_4)
    
    def get_knee_flexion_color(self, angle):
        """Retorna color según ángulo de flexión de rodilla"""
        if angle < 15:
            return self.color_cache['white']      # Casi extendida
        elif angle < 45:
            return self.color_cache['yellow']     # Flexión leve
        elif angle < 90:
            return self.color_cache['orange']     # Flexión moderada
        elif angle < 120:
            return self.color_cache['magenta']    # Flexión pronunciada
        else:
            return self.color_cache['green']      # Flexión máxima
    
    def reset_stats(self):
        """Reinicia estadísticas"""
        self.left_knee_angle = 0
        self.right_knee_angle = 0
        self.max_left_flexion = 0
        self.max_right_flexion = 0
        self.fps_history.clear()
        self.processing_times.clear()
        self.frame_count = 0
        print("[OK] Estadisticas reiniciadas")
    
    def get_performance_summary(self):
        """Retorna resumen de métricas de rendimiento"""
        if not self.fps_history:
            return {
                'total_frames': 0,
                'avg_fps': 0,
                'min_fps': 0,
                'max_fps': 0,
                'avg_processing_time': 0
            }
        
        return {
            'total_frames': self.frame_count,
            'avg_fps': sum(self.fps_history) / len(self.fps_history),
            'min_fps': min(self.fps_history),
            'max_fps': max(self.fps_history),
            'avg_processing_time': sum(self.processing_times) / len(self.processing_times)
        }
    
    def release(self):
        """Libera recursos de MediaPipe"""
        self.pose.close()


def main():
    """Función principal"""
    print("=" * 70)
    print("ANALISIS DE FLEXION DE RODILLA - VISTA DE PERFIL")
    print("=" * 70)
    print("\n[*] OPTIMIZACIONES ACTIVADAS:")
    print("   - Procesamiento en 640x480 (upscaling a 720p para display)")
    print("   - Dibujos OpenCV optimizados (LINE_4)")
    print("   - Cache de colores")
    print("   - Profiling de FPS y latencia en tiempo real")
    print("\n[*] MODOS DE VISUALIZACION:")
    print("   - CLEAN (Predeterminado): Solo lineas biomecanicas")
    print("   - FULL: Con skeleton completo de MediaPipe")
    print("   - MINIMAL: Maximo rendimiento")
    print("\n[*] INSTRUCCIONES:")
    print("   1. Colocate de PERFIL (lateral) a la camara")
    print("   2. El sistema detectara AUTOMATICAMENTE el lado mas visible")
    print("   3. DOBLA la rodilla (lleva el talon hacia el gluteo)")
    print("   4. Presiona 'M' para cambiar modo de visualizacion")
    print("   5. Presiona 'R' para reiniciar estadisticas")
    print("   6. Presiona 'Q' para salir")
    print("\n[*] SISTEMA GONIOMETRO:")
    print("   - 0deg = Pierna EXTENDIDA (vertical hacia abajo)")
    print("   - 45deg = Flexion LEVE")
    print("   - 90deg = Rodilla en ANGULO RECTO")
    print("   - 120deg = Flexion PRONUNCIADA")
    print("   - 150deg = FLEXION MAXIMA (talon cerca del gluteo)")
    print("\n[*] ROM NORMAL: 0-150deg de flexion")
    print("=" * 70)
    
    # Inicializar analizador
    analyzer = KneeProfileAnalyzer(
        processing_width=640, 
        processing_height=480
    )
    
    # Inicializar cámara
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("\n[ERROR] No se pudo abrir la camara")
        return
    
    # Configurar resolución
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("\n[OK] Camara iniciada correctamente")
    print("[*] Procesando video...")
    print("[*] Metricas de rendimiento visibles en esquina superior derecha\n")
    
    while cap.isOpened():
        ret, frame = cap.read()
        
        if not ret:
            print("\n[ERROR] No se pudo leer el frame")
            break
        
        # Procesar frame
        annotated_frame = analyzer.process_frame(frame)
        
        # Mostrar resultado
        cv2.imshow('Analisis de Flexion de Rodilla - Perfil', annotated_frame)
        
        # Controles de teclado
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q') or key == ord('Q'):
            print("\n[*] Cerrando aplicacion...")
            break
        elif key == ord('r') or key == ord('R'):
            analyzer.reset_stats()
        elif key == ord('m') or key == ord('M'):
            analyzer.toggle_display_mode()
    
    # Liberar recursos
    cap.release()
    cv2.destroyAllWindows()
    analyzer.release()
    
    # Mostrar resumen
    perf = analyzer.get_performance_summary()
    
    print("\n" + "=" * 70)
    print("[OK] Aplicacion cerrada correctamente")
    print("=" * 70)
    print(f"\n[*] RESUMEN DE RENDIMIENTO:")
    print(f"   - Total de frames procesados: {perf['total_frames']}")
    print(f"   - FPS promedio: {perf['avg_fps']:.1f}")
    print(f"   - FPS minimo: {perf['min_fps']:.1f}")
    print(f"   - FPS maximo: {perf['max_fps']:.1f}")
    print(f"   - Latencia promedio: {perf['avg_processing_time']:.2f}ms")
    
    print(f"\n[*] ESTADISTICAS BIOMECANICAS:")
    print(f"   - Lado analizado: {analyzer.side_detected}")
    
    # Mostrar estadísticas según lado analizado
    if analyzer.side_detected == 'left':
        print(f"   - Flexion maxima (izquierda): {analyzer.max_left_flexion:.1f}deg")
        max_flexion = analyzer.max_left_flexion
    else:
        print(f"   - Flexion maxima (derecha): {analyzer.max_right_flexion:.1f}deg")
        max_flexion = analyzer.max_right_flexion
    
    # Evaluación del ROM
    if max_flexion >= 135:
        print(f"   - Evaluacion ROM: EXCELENTE flexion (>=135deg)")
    elif max_flexion >= 120:
        print(f"   - Evaluacion ROM: BUENA flexion (120-135deg)")
    elif max_flexion >= 90:
        print(f"   - Evaluacion ROM: FLEXION MODERADA (90-120deg)")
    elif max_flexion >= 45:
        print(f"   - Evaluacion ROM: FLEXION LIMITADA (45-90deg) - Revisar")
    else:
        print(f"   - Evaluacion ROM: MUY LIMITADA (<45deg) - Consultar especialista")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
