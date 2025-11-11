"""
Script para análisis de ABDUCCIÓN bilateral de hombros (VISTA FRONTAL)
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

class ShoulderFrontalAnalyzer:
    def __init__(self, processing_width=640, processing_height=480):
        """
        Inicializa el analizador para vista FRONTAL (Abducción bilateral)
        
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
        
        # Variables para tracking de ángulos (abducción bilateral)
        self.left_abduction_angle = 0
        self.right_abduction_angle = 0
        self.max_left_abduction = 0
        self.max_right_abduction = 0
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
    
    def calculate_abduction_angle(self, shoulder, elbow):
        """
        Calcula el ángulo de abducción con eje vertical fijo
        
        Sistema goniómetro estándar:
        - Brazo FIJO: Eje vertical absoluto (0, 1)
        - Brazo MÓVIL: Línea del brazo (hombro → codo)
        - 0° = Brazo pegado al cuerpo
        - 90° = Brazo horizontal
        - 180° = Brazo completamente levantado
        """
        vertical_down_vector = np.array([0, 1])
        arm_vector = np.array([elbow[0] - shoulder[0], elbow[1] - shoulder[1]])
        
        arm_norm = np.linalg.norm(arm_vector)
        if arm_norm == 0:
            return 0
        
        arm_vector_normalized = arm_vector / arm_norm
        
        # Calcular ángulo
        dot_product = np.dot(vertical_down_vector, arm_vector_normalized)
        dot_product = np.clip(dot_product, -1.0, 1.0)
        angle = np.degrees(np.arccos(dot_product))
        
        return angle
    
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
            
            # Dibujar skeleton solo en modo FULL
            if self.display_mode == "FULL":
                mp_drawing.draw_landmarks(
                    image,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
                )
            
            # Procesar vista frontal
            self.process_frontal_view(image, landmarks, w, h)
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
    
    def process_frontal_view(self, image, landmarks, w, h):
        """Procesa vista frontal - Análisis de abducción bilateral"""
        # Obtener landmarks de ambos lados
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
        left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
        
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
        
        # Convertir a coordenadas 2D
        left_shoulder_2d = self.get_landmarks_2d(left_shoulder, w, h)
        left_hip_2d = self.get_landmarks_2d(left_hip, w, h)
        left_elbow_2d = self.get_landmarks_2d(left_elbow, w, h)
        left_wrist_2d = self.get_landmarks_2d(left_wrist, w, h)
        
        right_shoulder_2d = self.get_landmarks_2d(right_shoulder, w, h)
        right_hip_2d = self.get_landmarks_2d(right_hip, w, h)
        right_elbow_2d = self.get_landmarks_2d(right_elbow, w, h)
        right_wrist_2d = self.get_landmarks_2d(right_wrist, w, h)
        
        # Calcular ángulos de abducción
        left_angle = self.calculate_abduction_angle(left_shoulder_2d, left_elbow_2d)
        right_angle = self.calculate_abduction_angle(right_shoulder_2d, right_elbow_2d)
        
        # Actualizar estadísticas
        self.left_abduction_angle = left_angle
        self.right_abduction_angle = right_angle
        
        if left_angle > self.max_left_abduction:
            self.max_left_abduction = left_angle
        if right_angle > self.max_right_abduction:
            self.max_right_abduction = right_angle
        
        # Dibujar puntos clave
        # BRAZO IZQUIERDO
        cv2.circle(image, left_shoulder_2d, 8, self.color_cache['yellow'], -1, cv2.LINE_4)
        cv2.circle(image, left_hip_2d, 8, self.color_cache['magenta'], -1, cv2.LINE_4)
        cv2.circle(image, left_elbow_2d, 8, self.color_cache['cyan'], -1, cv2.LINE_4)
        
        # BRAZO DERECHO
        cv2.circle(image, right_shoulder_2d, 8, self.color_cache['yellow'], -1, cv2.LINE_4)
        cv2.circle(image, right_hip_2d, 8, self.color_cache['magenta'], -1, cv2.LINE_4)
        cv2.circle(image, right_elbow_2d, 8, self.color_cache['cyan'], -1, cv2.LINE_4)
        
        # Líneas de referencia verticales fijas
        vertical_length = 150
        
        # Eje vertical izquierdo
        left_vertical_start = (left_shoulder_2d[0], left_shoulder_2d[1] - vertical_length)
        left_vertical_end = (left_shoulder_2d[0], left_shoulder_2d[1] + vertical_length)
        cv2.line(image, left_vertical_start, left_vertical_end, self.color_cache['green'], 3, cv2.LINE_4)
        
        # Eje vertical derecho
        right_vertical_start = (right_shoulder_2d[0], right_shoulder_2d[1] - vertical_length)
        right_vertical_end = (right_shoulder_2d[0], right_shoulder_2d[1] + vertical_length)
        cv2.line(image, right_vertical_start, right_vertical_end, self.color_cache['green'], 3, cv2.LINE_4)
        
        # Líneas de los brazos
        cv2.line(image, left_shoulder_2d, left_elbow_2d, self.color_cache['blue'], 3, cv2.LINE_4)
        cv2.line(image, right_shoulder_2d, right_elbow_2d, self.color_cache['blue'], 3, cv2.LINE_4)
        
        # Antebrazos (solo en CLEAN y FULL)
        if self.display_mode != "MINIMAL":
            cv2.line(image, left_elbow_2d, left_wrist_2d, self.color_cache['blue'], 2, cv2.LINE_4)
            cv2.line(image, right_elbow_2d, right_wrist_2d, self.color_cache['blue'], 2, cv2.LINE_4)
        
        # Mostrar ángulos
        left_angle_text = f"{left_angle:.1f}deg"
        cv2.putText(image, left_angle_text, 
                   (left_shoulder_2d[0] - 60, left_shoulder_2d[1] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.4, self.color_cache['yellow'], 3, cv2.LINE_4)
        
        right_angle_text = f"{right_angle:.1f}deg"
        cv2.putText(image, right_angle_text, 
                   (right_shoulder_2d[0] + 20, right_shoulder_2d[1] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.4, self.color_cache['yellow'], 3, cv2.LINE_4)
        
        # Panel de información
        self.draw_info_panel(image, w, h)
    
    def draw_info_panel(self, image, w, h):
        """Dibuja el panel de información en la imagen"""
        # Panel superior con información
        panel_height = 230
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (w, panel_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
        
        # Título
        cv2.putText(image, "ANALISIS DE ABDUCCION BILATERAL (FRONTAL)", (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, self.color_cache['green'], 2, cv2.LINE_4)
        
        # Vista
        cv2.putText(image, "Vista: FRONTAL", (20, 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['white'], 2, cv2.LINE_4)
        
        # Ángulos actuales - BRAZO IZQUIERDO
        left_color = self.get_abduction_color(self.left_abduction_angle)
        cv2.putText(image, f"Brazo Izquierdo: {self.left_abduction_angle:.1f}deg", (20, 115),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, left_color, 2, cv2.LINE_4)
        cv2.putText(image, f"Max: {self.max_left_abduction:.1f}deg", (20, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['light_gray'], 2, cv2.LINE_4)
        
        # Ángulos actuales - BRAZO DERECHO
        right_color = self.get_abduction_color(self.right_abduction_angle)
        cv2.putText(image, f"Brazo Derecho: {self.right_abduction_angle:.1f}deg", (w//2 + 20, 115),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, right_color, 2, cv2.LINE_4)
        cv2.putText(image, f"Max: {self.max_right_abduction:.1f}deg", (w//2 + 20, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['light_gray'], 2, cv2.LINE_4)
        
        # Diferencia entre brazos
        diff = abs(self.left_abduction_angle - self.right_abduction_angle)
        diff_color = self.color_cache['green'] if diff < 10 else self.color_cache['orange'] if diff < 20 else self.color_cache['red']
        cv2.putText(image, f"Diferencia: {diff:.1f}deg", (20, 180),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, diff_color, 2, cv2.LINE_4)
        
        # Instrucciones
        cv2.putText(image, "Levanta ambos brazos lateralmente | 'R' reiniciar | 'M' cambiar modo | 'Q' salir", 
                   (20, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_cache['white'], 2, cv2.LINE_4)
    
    def get_abduction_color(self, angle):
        """Retorna color según el ángulo de abducción"""
        if angle < 15:
            return self.color_cache['white']
        elif angle < 45:
            return self.color_cache['yellow']
        elif angle < 90:
            return self.color_cache['orange']
        elif angle < 135:
            return self.color_cache['magenta']
        else:
            return self.color_cache['green']
    
    def reset_stats(self):
        """Reinicia todas las estadísticas"""
        self.left_abduction_angle = 0
        self.right_abduction_angle = 0
        self.max_left_abduction = 0
        self.max_right_abduction = 0
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
    print("ANALISIS DE ABDUCCION BILATERAL DE HOMBROS - VISTA FRONTAL")
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
    print("   1. Colocate de FRENTE a la camara")
    print("   2. Levanta ambos brazos lateralmente (ABDUCCION)")
    print("   3. El sistema mide AMBOS brazos simultaneamente")
    print("   4. Presiona 'M' para cambiar modo de visualizacion")
    print("   5. Presiona 'R' para reiniciar estadisticas")
    print("   6. Presiona 'Q' para salir")
    print("\n[*] SISTEMA GONIOMETRO:")
    print("   - 0deg = Brazos pegados al cuerpo")
    print("   - 90deg = Brazos HORIZONTALES (perpendiculares)")
    print("   - 180deg = Brazos completamente levantados (vertical)")
    print("\n[*] ANALISIS DE SIMETRIA:")
    print("   - Verde: Diferencia < 10deg (excelente)")
    print("   - Naranja: Diferencia 10-20deg (aceptable)")
    print("   - Rojo: Diferencia > 20deg (revisar)")
    print("=" * 70)
    
    # Inicializar analizador
    analyzer = ShoulderFrontalAnalyzer(processing_width=640, processing_height=480)
    
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
        cv2.imshow('Analisis de Hombro - Vista Frontal', annotated_frame)
        
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
    print(f"   - Abduccion maxima brazo izquierdo: {analyzer.max_left_abduction:.1f}deg")
    print(f"   - Abduccion maxima brazo derecho: {analyzer.max_right_abduction:.1f}deg")
    print(f"   - Diferencia entre brazos: {abs(analyzer.max_left_abduction - analyzer.max_right_abduction):.1f}deg")
    
    # Análisis de simetría
    diff = abs(analyzer.max_left_abduction - analyzer.max_right_abduction)
    if diff < 10:
        print(f"   - Evaluacion de simetria: EXCELENTE (diferencia < 10deg)")
    elif diff < 20:
        print(f"   - Evaluacion de simetria: ACEPTABLE (diferencia 10-20deg)")
    else:
        print(f"   - Evaluacion de simetria: REVISAR (diferencia > 20deg)")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
