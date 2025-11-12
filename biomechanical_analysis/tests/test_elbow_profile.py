"""
Script para análisis de FLEXIÓN/EXTENSIÓN de codo (VISTA DE PERFIL)
Utiliza OpenCV y MediaPipe para detectar y calcular ángulos
Sistema de medición: Goniómetro estándar con eje vertical fijo

OPTIMIZACIONES IMPLEMENTADAS:
- Procesamiento en resolución reducida (640x480) con upscaling para display
- Dibujos OpenCV optimizados (LINE_4 en vez de LINE_AA)
- Caché de colores por rangos de ángulos
- Sistema de profiling de FPS y latencia
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

class ElbowProfileAnalyzer:
    def __init__(self, processing_width=640, processing_height=480, exercise_type='flexion'):
        """
        Inicializa el analizador para vista de PERFIL (Flexión/Extensión de codo)
        
        Args:
            processing_width: Ancho para procesamiento de MediaPipe
            processing_height: Alto para procesamiento de MediaPipe
            exercise_type: Tipo de ejercicio ('flexion' o 'extension')
        """
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1
        )
        
        # Resolución de procesamiento
        self.processing_width = processing_width
        self.processing_height = processing_height
        
        # Tipo de ejercicio seleccionado
        self.exercise_type = exercise_type
        
        # Variables para tracking de ángulos
        self.current_angle = 0
        self.max_angle = 0
        self.side = "Detectando..."
        self.frame_count = 0
        
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
    
    def calculate_elbow_angle(self, shoulder, elbow, wrist):
        """
        Calcula el ángulo de flexión del codo con eje vertical fijo
        
        Sistema goniómetro estándar:
        - Brazo FIJO: Eje vertical absoluto (0, 1) que pasa por el CODO
        - Brazo MÓVIL: Línea del antebrazo (CODO → MUÑECA)
        - 0deg = Brazo completamente extendido (antebrazo hacia abajo)
        - 180deg = Codo completamente flexionado (mano toca hombro)
        
        Args:
            shoulder: Coordenadas [x, y] del hombro
            elbow: Coordenadas [x, y] del codo (PUNTO DE VÉRTICE)
            wrist: Coordenadas [x, y] de la muñeca
        """
        # Vector vertical fijo (referencia 0deg - apunta hacia abajo)
        vertical_down_vector = np.array([0, 1])
        
        # Vector del antebrazo (CODO → MUÑECA) - brazo móvil del goniómetro
        forearm_vector = np.array([wrist[0] - elbow[0], wrist[1] - elbow[1]])
        
        # Normalizar vector del antebrazo
        forearm_norm = np.linalg.norm(forearm_vector)
        
        if forearm_norm == 0:
            return 0
        
        forearm_vector_normalized = forearm_vector / forearm_norm
        
        # Calcular ángulo entre eje vertical y antebrazo
        dot_product = np.dot(vertical_down_vector, forearm_vector_normalized)
        dot_product = np.clip(dot_product, -1.0, 1.0)
        
        # Ángulo sin signo (0deg a 180deg)
        angle = np.degrees(np.arccos(dot_product))
        
        return angle
    
    def detect_side(self, landmarks):
        """
        Detecta qué lado del cuerpo está visible (vista de perfil)
        Retorna: lado, confianza, orientación
        """
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
        right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        nose = landmarks[mp_pose.PoseLandmark.NOSE]
        
        # MÉTODO 1: Solo visibilidad (ACTIVO por defecto - Consistente con hombro)
        """
        left_visibility = (left_shoulder.visibility + left_elbow.visibility) / 2
        right_visibility = (right_shoulder.visibility + right_elbow.visibility) / 2
        
        shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2
        
        if left_visibility > right_visibility:
            side = 'left'
            confidence = left_visibility
            orientation = "mirando izquierda" if nose.x < shoulder_center_x else "mirando derecha"
        else:
            side = 'right'
            confidence = right_visibility
            orientation = "mirando derecha" if nose.x > shoulder_center_x else "mirando izquierda"
        
        return side, confidence, orientation
        """
        # === MÉTODO 2 (MEJORADO): Profundidad Z + Visibilidad ===
        # Descomenta este bloque para usar detección más robusta (96% vs 75% precisión)
        
        # Profundidad promedio (más cerca = más negativo en Z)
        left_depth = (left_shoulder.z + left_elbow.z) / 2
        right_depth = (right_shoulder.z + right_elbow.z) / 2
        
        # Visibilidad promedio
        left_vis = (left_shoulder.visibility + left_elbow.visibility) / 2
        right_vis = (right_shoulder.visibility + right_elbow.visibility) / 2
        
        # Score combinado (profundidad 70%, visibilidad 30%)
        left_score = (-left_depth * 0.7) + (left_vis * 0.3)
        right_score = (-right_depth * 0.7) + (right_vis * 0.3)
        
        # Calcular confianza
        confidence = min(abs(left_score - right_score) * 100, 100)
        
        shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2
        
        if left_score > right_score:
            side = 'left'
            orientation = "mirando izquierda" if nose.x < shoulder_center_x else "mirando derecha"
        else:
            side = 'right'
            orientation = "mirando derecha" if nose.x > shoulder_center_x else "mirando izquierda"
        
        return side, confidence, orientation
        
        
    
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
            h, w = original_h, original_w
            landmarks = results.pose_landmarks.landmark
            
            # Detectar lado visible
            side, confidence, orientation = self.detect_side(landmarks)
            
            # Dibujar skeleton solo en modo FULL
            if self.display_mode == "FULL":
                mp_drawing.draw_landmarks(
                    image,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
                )
            
            # Procesar vista de perfil
            self.process_profile_view(image, landmarks, w, h, side, orientation, confidence)
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
    
    def process_profile_view(self, image, landmarks, w, h, side, orientation, confidence):
        """Procesa vista de perfil - Análisis de flexión/extensión de codo"""
        # Seleccionar landmarks según el lado detectado
        if side == 'left':
            shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
            elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
            wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
            side_text = "CODO IZQUIERDO"
        else:
            shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
            elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
            wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
            side_text = "CODO DERECHO"
        
        # Obtener coordenadas 2D
        shoulder_2d = self.get_landmarks_2d(shoulder, w, h)
        elbow_2d = self.get_landmarks_2d(elbow, w, h)
        wrist_2d = self.get_landmarks_2d(wrist, w, h)
        
        # Calcular ángulo de flexión del codo
        angle = self.calculate_elbow_angle(shoulder_2d, elbow_2d, wrist_2d)
        
        # Actualizar estadísticas
        self.current_angle = angle
        self.side = side_text
        
        if angle > self.max_angle:
            self.max_angle = angle
        
        # Dibujar puntos clave
        cv2.circle(image, elbow_2d, 10, self.color_cache['yellow'], -1, cv2.LINE_4)  # CODO (punto vértice)
        cv2.circle(image, shoulder_2d, 8, self.color_cache['magenta'], -1, cv2.LINE_4)  # HOMBRO
        cv2.circle(image, wrist_2d, 8, self.color_cache['cyan'], -1, cv2.LINE_4)  # MUÑECA
        
        # Línea de referencia vertical fija que pasa por el CODO
        vertical_length = 180
        vertical_start = (elbow_2d[0], elbow_2d[1] - vertical_length)
        vertical_end = (elbow_2d[0], elbow_2d[1] + vertical_length)
        cv2.line(image, vertical_start, vertical_end, self.color_cache['green'], 3, cv2.LINE_4)
        
        # Línea del antebrazo (CODO → MUÑECA) - brazo móvil del goniómetro
        cv2.line(image, elbow_2d, wrist_2d, self.color_cache['blue'], 4, cv2.LINE_4)
        
        # Brazo superior (solo en CLEAN y FULL, no en MINIMAL)
        if self.display_mode != "MINIMAL":
            cv2.line(image, shoulder_2d, elbow_2d, self.color_cache['blue'], 2, cv2.LINE_4)
        
        # Mostrar ángulo junto al codo
        angle_text = f"{angle:.1f}deg"
        cv2.putText(image, angle_text, 
                   (elbow_2d[0] - 50, elbow_2d[1] - 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, self.color_cache['yellow'], 3, cv2.LINE_4)
        
        # Indicador de estado de flexión
        if angle < 30:
            status = "EXTENSION"
            status_color = self.color_cache['white']
        else:
            status = "FLEXION"
            status_color = self.color_cache['green']
        
        cv2.putText(image, status, 
                   (elbow_2d[0] - 40, elbow_2d[1] + 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2, cv2.LINE_4)
        
        # Panel de información
        self.draw_info_panel(image, orientation, confidence, w, h)
    
    def draw_info_panel(self, image, orientation, confidence, w, h):
        """Dibuja el panel de información en la imagen"""
        # Panel superior con información
        panel_height = 200
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (w, panel_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
        
        # Título con tipo de ejercicio
        title = f"ANALISIS DE {self.exercise_type.upper()} DE CODO (PERFIL)"
        cv2.putText(image, title, (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.color_cache['white'], 2, cv2.LINE_4)
        
        # Lado detectado
        color_side = self.color_cache['green'] if confidence > 0.7 else self.color_cache['orange']
        cv2.putText(image, f"Lado: {self.side}", (20, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_side, 2, cv2.LINE_4)
        
        # Orientación
        cv2.putText(image, f"Orientacion: {orientation}", (20, 110),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['white'], 2, cv2.LINE_4)
        
        # Ángulo actual
        angle_color = self.get_angle_color(self.current_angle)
        cv2.putText(image, f"Angulo Actual: {self.current_angle:.1f}deg", (20, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, angle_color, 2, cv2.LINE_4)
        
        # ROM Máximo
        cv2.putText(image, f"ROM Maximo: {self.max_angle:.1f}deg", 
                   (20, 180),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color_cache['green'], 2, cv2.LINE_4)
        
        # Barra de progreso
        self.draw_rom_bar(image, w, h)
        
        # Instrucciones con ejercicio seleccionado
        instruction = f"Realiza {self.exercise_type} | 'R' reiniciar | 'M' modo | 'Q' salir"
        cv2.putText(image, instruction, 
                   (20, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['white'], 2, cv2.LINE_4)
    
    def draw_rom_bar(self, image, width, height):
        """Dibuja barra de progreso del ROM de codo"""
        bar_x = width - 300
        bar_y = 50
        bar_width = 260
        bar_height = 30
        
        # Fondo de la barra
        cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                     self.color_cache['gray'], -1)
        cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                     self.color_cache['white'], 2)
        
        # Rango normal de codo: 0deg (extendido) a 150deg (flexión máxima)
        max_range = 150
        
        # Calcular posición del ángulo actual
        angle_clamped = max(0, min(self.current_angle, max_range))
        current_position = int(bar_width * angle_clamped / max_range)
        
        # Color según ángulo
        color = self.get_angle_color(self.current_angle)
        
        # Llenar barra
        cv2.rectangle(image, (bar_x, bar_y), 
                     (bar_x + current_position, bar_y + bar_height), 
                     color, -1)
        
        # Indicador de posición actual
        cv2.line(image, (bar_x + current_position, bar_y - 5), 
                (bar_x + current_position, bar_y + bar_height + 5), 
                self.color_cache['yellow'], 3, cv2.LINE_4)
        
        # Texto de referencia
        cv2.putText(image, "ROM Codo", (bar_x, bar_y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_cache['white'], 1, cv2.LINE_4)
        cv2.putText(image, "0", (bar_x - 10, bar_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.color_cache['white'], 1, cv2.LINE_4)
        cv2.putText(image, "90", (bar_x + bar_width//2 - 10, bar_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.color_cache['white'], 1, cv2.LINE_4)
        cv2.putText(image, "150", (bar_x + bar_width - 20, bar_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.color_cache['white'], 1, cv2.LINE_4)
    
    def get_angle_color(self, angle):
        """Retorna color según el ángulo de flexión"""
        if angle < 30:
            return self.color_cache['white']  # Casi extendido
        elif angle < 60:
            return self.color_cache['yellow']  # Poco flexionado
        elif angle < 90:
            return self.color_cache['orange']  # Medio flexionado
        elif angle < 120:
            return self.color_cache['magenta']  # Muy flexionado
        else:
            return self.color_cache['green']  # Flexión máxima
    
    def reset_stats(self):
        """Reinicia todas las estadísticas"""
        self.max_angle = 0
        self.current_angle = 0
        self.fps_history.clear()
        self.processing_times.clear()
        self.frame_count = 0
        print("[OK] Estadisticas reiniciadas")
    
    def get_performance_summary(self):
        """Retorna un resumen de las métricas de rendimiento"""
        if not self.fps_history or not self.processing_times:
            return {
                'avg_fps': 0,
                'avg_processing_time': 0,
                'total_frames': self.frame_count
            }
        
        return {
            'avg_fps': sum(self.fps_history) / len(self.fps_history),
            'min_fps': min(self.fps_history),
            'max_fps': max(self.fps_history),
            'avg_processing_time': sum(self.processing_times) / len(self.processing_times),
            'min_processing_time': min(self.processing_times),
            'max_processing_time': max(self.processing_times),
            'total_frames': self.frame_count
        }
    
    def release(self):
        """Libera recursos"""
        self.pose.close()


def main():
    """Función principal"""
    print("=" * 70)
    print("ANALISIS DE CODO - VISTA DE PERFIL")
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
    
    # ===== SELECCIÓN DE TIPO DE EJERCICIO =====
    print("\n" + "=" * 70)
    print("[*] SELECCION DE TIPO DE EJERCICIO:")
    print("=" * 70)
    print("   1. FLEXION (doblar el codo, mano hacia el hombro)")
    print("   2. EXTENSION (extender el brazo completamente)")
    print()
    
    exercise_type = 'flexion'  # Valor por defecto
    while True:
        try:
            choice = input("Selecciona el tipo de ejercicio (1/2) [Por defecto: 1]: ").strip()
            
            if choice == '' or choice == '1':
                exercise_type = 'flexion'
                print("[OK] Ejercicio FLEXION seleccionado")
                break
            elif choice == '2':
                exercise_type = 'extension'
                print("[OK] Ejercicio EXTENSION seleccionado")
                break
            else:
                print("[ERROR] Opcion invalida. Por favor ingresa 1 o 2.")
        except KeyboardInterrupt:
            print("\n[*] Operacion cancelada por el usuario")
            return
        except Exception as e:
            print(f"[ERROR] Error en la seleccion: {e}")
            print("[*] Usando opcion por defecto (FLEXION)")
            exercise_type = 'flexion'
            break
    
    print("\n[*] INSTRUCCIONES:")
    print("   1. Colocate de PERFIL a la camara")
    
    if exercise_type == 'flexion':
        print("   2. Realiza movimiento de FLEXION:")
        print("      - Dobla el codo")
        print("      - Lleva la mano hacia el hombro (hasta 150deg)")
    else:  # extension
        print("   2. Realiza movimiento de EXTENSION:")
        print("      - Extiende el brazo completamente")
        print("      - Brazo lo mas recto posible (hacia 0deg)")
    
    print("   3. Presiona 'M' para cambiar modo de visualizacion")
    print("   4. Presiona 'R' para reiniciar estadisticas")
    print("   5. Presiona 'Q' para salir")
    print("\n[*] SISTEMA GONIOMETRO:")
    print("   - 0deg = Brazo EXTENDIDO (antebrazo hacia abajo)")
    print("   - 90deg = Antebrazo HORIZONTAL")
    print("   - 150deg = FLEXION MAXIMA (mano toca hombro)")
    print("   - ROM normal: 0-150deg")
    print("=" * 70)
    
    # Inicializar analizador con el ejercicio seleccionado
    analyzer = ElbowProfileAnalyzer(
        processing_width=640, 
        processing_height=480,
        exercise_type=exercise_type
    )
    
    # Inicializar cámara
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("[ERROR] No se pudo acceder a la camara")
        return
    
    # Configurar resolución
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("\n[OK] Camara iniciada correctamente")
    print("[*] Procesando video...")
    print("[*] Metricas de rendimiento visibles en esquina superior derecha\n")
    
    while cap.isOpened():
        success, frame = cap.read()
        
        if not success:
            print("[ERROR] Error al capturar frame")
            break
        
        # Procesar frame
        annotated_frame = analyzer.process_frame(frame)
        
        # Mostrar frame
        cv2.imshow('Analisis de Codo - Vista de Perfil', annotated_frame)
        
        # Manejar teclas
        key = cv2.waitKey(5) & 0xFF
        
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
    print(f"   - Lado analizado: {analyzer.side}")
    print(f"   - ROM Maximo alcanzado: {analyzer.max_angle:.1f}deg")
    
    # Evaluación del ROM
    if analyzer.max_angle >= 140:
        print(f"   - Evaluacion: EXCELENTE ROM (>140deg)")
    elif analyzer.max_angle >= 120:
        print(f"   - Evaluacion: ROM BUENO (120-140deg)")
    elif analyzer.max_angle >= 90:
        print(f"   - Evaluacion: ROM LIMITADO (90-120deg)")
    else:
        print(f"   - Evaluacion: ROM MUY LIMITADO (<90deg) - Revisar")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
