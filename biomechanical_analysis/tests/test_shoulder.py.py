"""
Script independiente para análisis de movimiento de hombro en tiempo real
Utiliza OpenCV y MediaPipe para detectar y calcular ángulos
- Vista de PERFIL: Analiza extensión/flexión del hombro visible
- Vista FRONTAL: Analiza abducción bilateral de ambos hombros simultáneamente
"""

import cv2
import mediapipe as mp
import numpy as np
import math

# Inicializar MediaPipe Pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

class ShoulderExtensionAnalyzer:
    def __init__(self):
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1
        )
        
        # 🎯 GONIÓMETRO: Variables para tracking - SIEMPRE POSITIVO
        self.current_angle = 0
        self.max_angle = 0  # Máximo ROM alcanzado (siempre positivo como goniómetro)
        self.side = "Detectando..."
        
        # Variables para tracking de ángulos - Vista frontal (abducción)
        self.left_abduction_angle = 0
        self.right_abduction_angle = 0
        self.max_left_abduction = 0
        self.max_right_abduction = 0
        
        # Variable para detectar orientación
        self.view_type = "Detectando..."  # "PERFIL" o "FRONTAL"
        
        self.frame_count = 0
        
    def calculate_angle(self, point1, point2, point3):
        """
        Calcula el ángulo entre tres puntos
        point1: primer punto (ej: cadera)
        point2: vértice del ángulo (ej: hombro)
        point3: tercer punto (ej: codo)
        """
        # Convertir a arrays numpy
        p1 = np.array(point1)
        p2 = np.array(point2)
        p3 = np.array(point3)
        
        # Calcular vectores
        vector1 = p1 - p2
        vector2 = p3 - p2
        
        # Calcular ángulo usando producto punto
        cosine_angle = np.dot(vector1, vector2) / (np.linalg.norm(vector1) * np.linalg.norm(vector2))
        
        # Evitar errores de dominio
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        
        angle = np.degrees(np.arccos(cosine_angle))
        
        return angle
    
    def calculate_extension_angle(self, shoulder, hip, elbow, side):
        """
        🎯 SISTEMA GONIÓMETRO CON DIRECCIÓN
        
        Backend mantiene signos para distinguir movimientos:
        - 0° = Posición neutra (brazo apuntando ABAJO)
        - Positivo (+) = Flexión (hacia adelante/arriba)
        - Negativo (-) = Extensión (hacia atrás)
        
        Display usa abs() para mostrar siempre positivo
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
        cross_product = down_vector[0] * arm_vector[1] - down_vector[1] * arm_vector[0]
        
        # Determinar el signo según el lado y la dirección
        if side == 'left':
            if cross_product > 0:
                angle = angle_magnitude  # Adelante = POSITIVO
            else:
                angle = -angle_magnitude  # Atrás = NEGATIVO
        else:  # side == 'right'
            if cross_product < 0:
                angle = angle_magnitude  # Adelante = POSITIVO
            else:
                angle = -angle_magnitude  # Atrás = NEGATIVO
        
        return angle  # ✅ Con signo: +flexión, -extensión
    
    def calculate_abduction_angle(self, shoulder, hip, elbow):
        """
        Calcula el ángulo de abducción del hombro (vista frontal)
        - 0° = Brazo pegado al cuerpo (paralelo a la línea hombro-cadera)
        - 90° = Brazo horizontal (perpendicular al cuerpo)
        - 180° = Brazo completamente levantado sobre la cabeza
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
    
    def detect_side_and_visibility(self, landmarks):
        """
        Detecta qué lado del cuerpo está visible y hacia dónde mira la persona
        También determina si está de PERFIL o FRONTAL
        Retorna: tipo_vista, lado (para perfil), confianza, orientación
        """
        # Obtener puntos clave
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        nose = landmarks[mp_pose.PoseLandmark.NOSE]
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        
        # Calcular visibilidad de cada lado
        left_visibility = left_shoulder.visibility
        right_visibility = right_shoulder.visibility
        
        # Calcular distancia entre hombros (en coordenadas normalizadas)
        shoulder_distance = abs(right_shoulder.x - left_shoulder.x)
        
        # Calcular distancia entre caderas
        hip_distance = abs(right_hip.x - left_hip.x)
        
        # Determinar si está de FRENTE o PERFIL
        # Si ambos hombros son muy visibles Y la distancia entre ellos es grande = FRONTAL
        # Umbral: si la distancia entre hombros > 0.15 (normalizado) = probablemente frontal
        
        avg_shoulder_visibility = (left_visibility + right_visibility) / 2
        
        if shoulder_distance > 0.12 and avg_shoulder_visibility > 0.6 and left_visibility > 0.5 and right_visibility > 0.5:
            # Vista FRONTAL
            view_type = "FRONTAL"
            side = None  # No aplica en vista frontal
            confidence = avg_shoulder_visibility
            orientation = "de frente"
        else:
            # Vista de PERFIL
            view_type = "PERFIL"
            
            # Determinar orientación basado en la posición de la nariz respecto a los hombros
            nose_x = nose.x
            left_shoulder_x = left_shoulder.x
            right_shoulder_x = right_shoulder.x
            
            shoulder_center_x = (left_shoulder_x + right_shoulder_x) / 2
            
            # Calcular qué hombro está más de perfil (más visible y más alejado de la nariz)
            if left_visibility > right_visibility:
                # Hombro izquierdo más visible
                side = 'left'
                confidence = left_visibility
                orientation = "mirando izquierda" if nose_x < shoulder_center_x else "mirando derecha"
            else:
                # Hombro derecho más visible
                side = 'right'
                confidence = right_visibility
                orientation = "mirando derecha" if nose_x > shoulder_center_x else "mirando izquierda"
        
        return view_type, side, confidence, orientation
    
    def get_landmarks_2d(self, landmark, frame_width, frame_height):
        """Convierte landmarks normalizados a coordenadas de píxeles"""
        return [int(landmark.x * frame_width), int(landmark.y * frame_height)]
    
    def draw_angle_arc(self, image, center, start_point, end_point, angle, color):
        """Dibuja un arco para visualizar el ángulo"""
        radius = 50
        
        # Calcular ángulos de inicio y fin
        start_angle = math.degrees(math.atan2(start_point[1] - center[1], start_point[0] - center[0]))
        end_angle = math.degrees(math.atan2(end_point[1] - center[1], end_point[0] - center[0]))
        
        # Dibujar arco
        cv2.ellipse(image, center, (radius, radius), 0, start_angle, end_angle, color, 2)
    
    def process_frame(self, frame):
        """Procesa un frame y retorna el frame anotado"""
        self.frame_count += 1
        
        # Convertir BGR a RGB
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False
        
        # Procesar con MediaPipe
        results = self.pose.process(image_rgb)
        
        # Convertir de vuelta a BGR
        image_rgb.flags.writeable = True
        image = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        
        if results.pose_landmarks:
            # Obtener dimensiones del frame
            h, w, _ = image.shape
            
            landmarks = results.pose_landmarks.landmark
            
            # Detectar tipo de vista (PERFIL o FRONTAL)
            view_type, side, confidence, orientation = self.detect_side_and_visibility(landmarks)
            self.view_type = view_type
            
            # Dibujar skeleton
            mp_drawing.draw_landmarks(
                image,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
            )
            
            if view_type == "FRONTAL":
                # MODO FRONTAL - Analizar ABDUCCIÓN bilateral
                self.process_frontal_view(image, landmarks, w, h, orientation, confidence)
            else:
                # MODO PERFIL - Analizar EXTENSIÓN de un solo hombro
                self.process_profile_view(image, landmarks, w, h, side, orientation, confidence)
        else:
            # No se detectó persona
            cv2.putText(image, "No se detecta persona", (50, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        return image
    
    def process_profile_view(self, image, landmarks, w, h, side, orientation, confidence):
        """Procesa vista de perfil - Análisis de extensión"""
        # Seleccionar landmarks según el lado detectado
        if side == 'left':
            shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
            hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
            elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
            wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
            side_text = "HOMBRO IZQUIERDO"
        else:
            shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
            hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
            elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
            wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
            side_text = "HOMBRO DERECHO"
        
        # Obtener coordenadas 2D
        shoulder_2d = self.get_landmarks_2d(shoulder, w, h)
        hip_2d = self.get_landmarks_2d(hip, w, h)
        elbow_2d = self.get_landmarks_2d(elbow, w, h)
        wrist_2d = self.get_landmarks_2d(wrist, w, h)
        
        # Calcular ángulo de extensión (CON SIGNO: +flexión, -extensión)
        angle = self.calculate_extension_angle(shoulder_2d, hip_2d, elbow_2d, side)
        
        # Actualizar estadísticas
        self.current_angle = angle
        self.side = side_text
        
        # 🎯 GONIÓMETRO: Actualizar máximo ROM (usar abs() para tracking)
        abs_angle = abs(angle)
        if abs_angle > self.max_angle:
            self.max_angle = abs_angle
        
        # Dibujar puntos clave más grandes
        cv2.circle(image, shoulder_2d, 8, (0, 255, 255), -1)  # Amarillo
        cv2.circle(image, hip_2d, 8, (255, 0, 255), -1)      # Magenta
        cv2.circle(image, elbow_2d, 8, (255, 255, 0), -1)    # Cyan
        
        # Dibujar líneas de referencia
        cv2.line(image, hip_2d, shoulder_2d, (0, 255, 0), 2)       # Verde - Línea vertical
        cv2.line(image, shoulder_2d, elbow_2d, (255, 0, 0), 2)     # Azul - Brazo
        cv2.line(image, elbow_2d, wrist_2d, (255, 0, 0), 2)        # Azul - Antebrazo
        
        # Mostrar ángulo en el hombro (abs() para display, pero mostrar signo para debug)
        angle_text = f"{abs(angle):.1f}°"
        # Agregar indicador de dirección
        direction_text = "FLEX" if angle > 0 else "EXT" if angle < 0 else ""
        cv2.putText(image, angle_text, 
                   (shoulder_2d[0] - 40, shoulder_2d[1] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
        if direction_text:
            cv2.putText(image, direction_text, 
                       (shoulder_2d[0] - 30, shoulder_2d[1] + 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0) if angle > 0 else (255, 165, 0), 2)
        
        # Panel de información
        self.draw_info_panel_profile(image, orientation, confidence)
    
    def process_frontal_view(self, image, landmarks, w, h, orientation, confidence):
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
        
        # Calcular ángulos de abducción para ambos lados
        left_angle = self.calculate_abduction_angle(left_shoulder_2d, left_hip_2d, left_elbow_2d)
        right_angle = self.calculate_abduction_angle(right_shoulder_2d, right_hip_2d, right_elbow_2d)
        
        # Actualizar estadísticas
        self.left_abduction_angle = left_angle
        self.right_abduction_angle = right_angle
        
        if left_angle > self.max_left_abduction:
            self.max_left_abduction = left_angle
        if right_angle > self.max_right_abduction:
            self.max_right_abduction = right_angle
        
        # Dibujar puntos clave - BRAZO IZQUIERDO
        cv2.circle(image, left_shoulder_2d, 8, (0, 255, 255), -1)  # Amarillo
        cv2.circle(image, left_hip_2d, 8, (255, 0, 255), -1)      # Magenta
        cv2.circle(image, left_elbow_2d, 8, (255, 255, 0), -1)    # Cyan
        
        # Dibujar puntos clave - BRAZO DERECHO
        cv2.circle(image, right_shoulder_2d, 8, (0, 255, 255), -1)  # Amarillo
        cv2.circle(image, right_hip_2d, 8, (255, 0, 255), -1)      # Magenta
        cv2.circle(image, right_elbow_2d, 8, (255, 255, 0), -1)    # Cyan
        
        # Dibujar líneas de referencia - BRAZO IZQUIERDO
        cv2.line(image, left_hip_2d, left_shoulder_2d, (0, 255, 0), 2)       # Verde - Línea vertical
        cv2.line(image, left_shoulder_2d, left_elbow_2d, (255, 0, 0), 3)     # Azul - Brazo
        cv2.line(image, left_elbow_2d, left_wrist_2d, (255, 0, 0), 3)        # Azul - Antebrazo
        
        # Dibujar líneas de referencia - BRAZO DERECHO
        cv2.line(image, right_hip_2d, right_shoulder_2d, (0, 255, 0), 2)     # Verde - Línea vertical
        cv2.line(image, right_shoulder_2d, right_elbow_2d, (255, 0, 0), 3)   # Azul - Brazo
        cv2.line(image, right_elbow_2d, right_wrist_2d, (255, 0, 0), 3)      # Azul - Antebrazo
        
        # Mostrar ángulos en ambos hombros
        left_angle_text = f"{left_angle:.1f}"
        cv2.putText(image, left_angle_text, 
                   (left_shoulder_2d[0] - 60, left_shoulder_2d[1] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 255, 255), 3)
        
        right_angle_text = f"{right_angle:.1f}"
        cv2.putText(image, right_angle_text, 
                   (right_shoulder_2d[0] + 20, right_shoulder_2d[1] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 255, 255), 3)
        
        # Panel de información
        self.draw_info_panel_frontal(image, orientation, confidence)
    
    def draw_info_panel_profile(self, image, orientation, confidence):
        """Dibuja el panel de información en la imagen - Vista de perfil"""
        h, w, _ = image.shape
        
        # Panel superior con información
        panel_height = 200
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (w, panel_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
        
        # Título
        cv2.putText(image, "ANALISIS DE EXTENSION/FLEXION DE HOMBRO (PERFIL)", (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Lado detectado
        color_side = (0, 255, 0) if confidence > 0.7 else (0, 165, 255)
        cv2.putText(image, f"Lado: {self.side}", (20, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_side, 2)
        
        # Orientación
        cv2.putText(image, f"Orientacion: {orientation}", (20, 110),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Ángulo actual (siempre positivo para el usuario)
        angle_color = self.get_angle_color(self.current_angle)
        # 🎯 GONIÓMETRO: Mostrar abs() + indicador direccional
        direction_text = "FLEX" if self.current_angle > 0 else "EXT" if self.current_angle < 0 else ""
        cv2.putText(image, f"Angulo Actual: {abs(self.current_angle):.1f} {direction_text}", (20, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, angle_color, 2)
        
        # 🎯 GONIÓMETRO: Solo mostrar máximo ROM (siempre positivo)
        cv2.putText(image, f"ROM Maximo: {self.max_angle:.1f}", 
                   (20, 180),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Barra de progreso de extensión
        self.draw_extension_bar(image, w, h)
        
        # Instrucciones
        cv2.putText(image, "Presiona 'R' para reiniciar | 'Q' para salir", 
                   (20, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    def draw_info_panel_frontal(self, image, orientation, confidence):
        """Dibuja el panel de información en la imagen - Vista frontal"""
        h, w, _ = image.shape
        
        # Panel superior con información
        panel_height = 230
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (w, panel_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
        
        # Título
        cv2.putText(image, "ANALISIS DE ABDUCCION BILATERAL (FRONTAL)", (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        # Orientación
        cv2.putText(image, f"Vista: {orientation} (FRONTAL)", (20, 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Ángulos actuales - BRAZO IZQUIERDO
        left_color = self.get_abduction_color(self.left_abduction_angle)
        cv2.putText(image, f"Brazo Izquierdo: {self.left_abduction_angle:.1f}", (20, 115),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, left_color, 2)
        cv2.putText(image, f"Max: {self.max_left_abduction:.1f}", (20, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        
        # Ángulos actuales - BRAZO DERECHO
        right_color = self.get_abduction_color(self.right_abduction_angle)
        cv2.putText(image, f"Brazo Derecho: {self.right_abduction_angle:.1f}", (w//2 + 20, 115),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, right_color, 2)
        cv2.putText(image, f"Max: {self.max_right_abduction:.1f}", (w//2 + 20, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        
        # Barras de progreso de abducción
        self.draw_abduction_bars(image, w, h)
        
        # Instrucciones
        cv2.putText(image, "Levanta ambos brazos lateralmente | 'R' para reiniciar | 'Q' para salir", 
                   (20, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    def get_angle_color(self, angle):
        """Retorna color según el ángulo y dirección"""
        abs_angle = abs(angle)
        
        if abs_angle < 15:
            return (255, 255, 255)  # Blanco - Cerca de posición neutral (brazo abajo)
        elif abs_angle < 45:
            return (0, 255, 255)    # Amarillo - Elevación baja
        elif abs_angle < 90:
            return (0, 165, 255)    # Naranja - Elevación media (horizontal)
        elif abs_angle < 135:
            return (255, 0, 255)    # Magenta - Elevación alta
        else:
            return (0, 255, 0)      # Verde - Cerca de 180° (brazo arriba)
    
    def get_abduction_color(self, angle):
        """Retorna color según el ángulo de abducción"""
        if angle < 15:
            return (255, 255, 255)  # Blanco - Brazo pegado al cuerpo
        elif angle < 45:
            return (0, 255, 255)    # Amarillo - Elevación baja
        elif angle < 90:
            return (0, 165, 255)    # Naranja - Acercándose a horizontal
        elif angle < 135:
            return (255, 0, 255)    # Magenta - Por encima de horizontal
        else:
            return (0, 255, 0)      # Verde - Cerca de vertical (arriba)
    
    def draw_extension_bar(self, image, width, height):
        """🎯 Dibuja barra de progreso del ROM - SISTEMA GONIÓMETRO (0° a 180°)"""
        bar_x = width - 300
        bar_y = 50
        bar_width = 260
        bar_height = 30
        
        # Fondo de la barra
        cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                     (50, 50, 50), -1)
        cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                     (255, 255, 255), 2)
        
        # 🎯 GONIÓMETRO: Rango 0° a 180° (siempre positivo)
        min_range = 0
        max_range = 180
        total_range = max_range - min_range
        
        # 🎯 GONIÓMETRO: Usar abs() para visualización
        abs_current_angle = abs(self.current_angle)
        
        # Calcular posición del ángulo actual
        angle_clamped = max(min_range, min(abs_current_angle, max_range))
        current_position = int(bar_width * (angle_clamped - min_range) / total_range)
        
        # Color según magnitud (goniómetro)
        if angle_clamped < 45:
            color = (0, 255, 255)  # Amarillo - Rango bajo
        elif angle_clamped < 90:
            color = (0, 165, 255)  # Naranja - Rango medio-bajo
        elif angle_clamped < 135:
            color = (255, 0, 255)  # Magenta - Rango medio-alto
        else:
            color = (0, 255, 0)    # Verde - Rango alto
        
        # Llenar barra desde 0° hasta posición actual
        cv2.rectangle(image, (bar_x, bar_y), 
                     (bar_x + current_position, bar_y + bar_height), 
                     color, -1)
        
        # Dibujar indicador de posición actual
        cv2.line(image, (bar_x + current_position, bar_y - 5), 
                (bar_x + current_position, bar_y + bar_height + 5), 
                (0, 255, 255), 3)
        
        # Texto de referencia
        cv2.putText(image, "ROM (Goniometro)", (bar_x, bar_y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "0", (bar_x - 10, bar_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(image, "90", (bar_x + bar_width//2 - 10, bar_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(image, "180", (bar_x + bar_width - 20, bar_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    def draw_abduction_bars(self, image, width, height):
        """Dibuja barras de progreso para abducción bilateral"""
        # Posición y tamaño de las barras
        bar_width = 40
        bar_height = 250
        bar_y = 180
        
        # Barra izquierda (brazo izquierdo)
        left_bar_x = 100
        
        # Barra derecha (brazo derecho)
        right_bar_x = width - 150
        
        # Dibujar ambas barras
        for bar_x, angle, max_angle, side_label in [
            (left_bar_x, self.left_abduction_angle, self.max_left_abduction, "IZQ"),
            (right_bar_x, self.right_abduction_angle, self.max_right_abduction, "DER")
        ]:
            # Fondo de la barra
            cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                         (50, 50, 50), -1)
            cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                         (255, 255, 255), 2)
            
            # Rango: 0° (abajo) a 180° (arriba)
            max_range = 180
            
            # Calcular altura de llenado
            angle_clamped = max(0, min(angle, max_range))
            fill_height = int(bar_height * angle_clamped / max_range)
            
            # Color según ángulo
            color = self.get_abduction_color(angle)
            
            # Llenar barra desde abajo hacia arriba
            if fill_height > 0:
                cv2.rectangle(image, 
                             (bar_x, bar_y + bar_height - fill_height), 
                             (bar_x + bar_width, bar_y + bar_height), 
                             color, -1)
            
            # Marcas de referencia
            for mark_angle, mark_y in [(0, bar_height), (45, bar_height * 3/4), 
                                        (90, bar_height / 2), (135, bar_height / 4), 
                                        (180, 0)]:
                y_pos = int(bar_y + mark_y)
                cv2.line(image, (bar_x - 5, y_pos), (bar_x, y_pos), (200, 200, 200), 1)
                if mark_angle in [0, 90, 180]:
                    cv2.putText(image, f"{int(mark_angle)}", (bar_x - 30, y_pos + 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 200, 200), 1)
            
            # Etiqueta del lado
            cv2.putText(image, side_label, (bar_x + 5, bar_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            # Valor actual y máximo
            cv2.putText(image, f"{angle:.0f}", (bar_x + 5, bar_y + bar_height + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            cv2.putText(image, f"Max:{max_angle:.0f}", (bar_x - 10, bar_y + bar_height + 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
    
    def reset_stats(self):
        """Reinicia todas las estadísticas"""
        # Vista de perfil - GONIÓMETRO (solo máximo positivo)
        self.max_angle = 0
        self.current_angle = 0
        
        # Vista frontal
        self.left_abduction_angle = 0
        self.right_abduction_angle = 0
        self.max_left_abduction = 0
        self.max_right_abduction = 0
        
        print("✅ Estadísticas reiniciadas - Sistema goniómetro (solo valores positivos)")
    
    def release(self):
        """Libera recursos"""
        self.pose.close()


def main():
    """Función principal"""
    print("=" * 70)
    print("ANÁLISIS DE MOVIMIENTO DE HOMBRO EN TIEMPO REAL")
    print("=" * 70)
    print("\n🔄 DETECCIÓN AUTOMÁTICA DE ORIENTACIÓN:")
    print("   • VISTA DE PERFIL → Análisis de EXTENSIÓN/FLEXIÓN")
    print("   • VISTA FRONTAL → Análisis de ABDUCCIÓN BILATERAL")
    print("\n📋 INSTRUCCIONES:")
    print("   1. Colócate frente a la cámara")
    print("   2. El sistema detectará automáticamente tu orientación")
    print("   3. Realiza movimientos según la vista detectada:")
    print("")
    print("      🔸 VISTA DE PERFIL:")
    print("         - Brazo hacia adelante y atrás")
    print("         - Brazo hacia arriba y abajo")
    print("")
    print("      🔸 VISTA FRONTAL:")
    print("         - Levanta ambos brazos lateralmente (abducción)")
    print("         - Ambos ángulos se miden simultáneamente")
    print("")
    print("   4. Presiona 'R' para reiniciar estadísticas")
    print("   5. Presiona 'Q' para salir")
    print("\n📐 SISTEMA GONIÓMETRO (0° a 180°):")
    print("\n   ✅ TODOS LOS ÁNGULOS SON POSITIVOS (como goniómetro real)")
    print("\n   VISTA DE PERFIL (Flexión/Extensión):")
    print("   - 0° = Brazo apuntando hacia ABAJO (posición neutra)")
    print("   - 90° = Brazo en posición HORIZONTAL")
    print("   - 180° = Brazo apuntando hacia ARRIBA (sobre la cabeza)")
    print("   - Flexión (adelante) y Extensión (atrás) = SIEMPRE POSITIVO")
    print("\n   VISTA FRONTAL (Abducción):")
    print("   - 0° = Brazos pegados al cuerpo (posición neutra)")
    print("   - 90° = Brazos horizontales (perpendiculares al cuerpo)")
    print("   - 180° = Brazos completamente levantados sobre la cabeza")
    print("=" * 70)
    
    # Inicializar analizador
    analyzer = ShoulderExtensionAnalyzer()
    
    # Inicializar cámara
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: No se pudo acceder a la cámara")
        return
    
    # Configurar resolución
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("\n✅ Cámara iniciada correctamente")
    print("📹 Procesando video...\n")
    
    while cap.isOpened():
        success, frame = cap.read()
        
        if not success:
            print("❌ Error al capturar frame")
            break
        
        # Procesar frame
        annotated_frame = analyzer.process_frame(frame)
        
        # Mostrar frame
        cv2.imshow('Análisis de Movimiento de Hombro', annotated_frame)
        
        # Manejar teclas
        key = cv2.waitKey(5) & 0xFF
        
        if key == ord('q') or key == ord('Q'):
            print("\n👋 Cerrando aplicación...")
            break
        elif key == ord('r') or key == ord('R'):
            analyzer.reset_stats()
    
    # Liberar recursos
    cap.release()
    cv2.destroyAllWindows()
    analyzer.release()
    
    print("\n✅ Aplicación cerrada correctamente")
    print(f"📊 Estadísticas finales:")
    print(f"   - Tipo de vista: {analyzer.view_type}")
    
    if analyzer.view_type == "PERFIL":
        print(f"   - Lado analizado: {analyzer.side}")
        print(f"   - Máximo hacia adelante: {analyzer.max_angle:.1f}°")
        print(f"   - Máximo hacia atrás: {analyzer.min_angle:.1f}°")
        print(f"   - Rango total de movimiento: {analyzer.max_angle - analyzer.min_angle:.1f}°")
    elif analyzer.view_type == "FRONTAL":
        print(f"   - Abducción brazo izquierdo: {analyzer.max_left_abduction:.1f}°")
        print(f"   - Abducción brazo derecho: {analyzer.max_right_abduction:.1f}°")
        print(f"   - Diferencia entre brazos: {abs(analyzer.max_left_abduction - analyzer.max_right_abduction):.1f}°")


if __name__ == "__main__":
    main()
