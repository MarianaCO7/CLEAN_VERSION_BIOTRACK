# Crear: biomechanical_analysis/tests/test_neck.py

"""
🦴 TEST DE CUELLO CON GUÍA INTELIGENTE
🧠 Sistema completo de análisis cervical
"""

import sys
import os
import cv2
import time
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# 🔇 SILENCIAR MENSAJES DE TENSORFLOW
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Configurar path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from joints.neck_analyzer import NeckAnalyzer
from guides.neck_exercise_guide import NeckExerciseGuide
from core.camera_manager import auto_setup_camera_for_biomechanics, diagnose_camera_problems

def draw_text_with_pil(frame, text, position, font_size=20, color=(255, 255, 255)):
    """📝 Dibujar texto con PIL para símbolos correctos"""
    
    # Convertir a PIL
    pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_image)
    
    # Cargar fuente
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Dibujar texto
    draw.text(position, text, font=font, fill=color)
    
    # Convertir de vuelta
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

def main():
    """
    🦴 TEST DE CUELLO CON SISTEMA COMPLETO
    🧠 Flexión/Extensión + Inclinación lateral
    """
    
    try:
        # 🎥 CONFIGURACIÓN AUTOMÁTICA DE CÁMARA
        print("🎥 CONFIGURANDO CÁMARA PARA ANÁLISIS DE CUELLO...")
        camera_id, camera_info = auto_setup_camera_for_biomechanics()
        
        # 🦴 INICIALIZAR ANALIZADORES
        analyzer = NeckAnalyzer()
        exercise_guide = NeckExerciseGuide()
        cap = cv2.VideoCapture(camera_id)
        
        # 🎯 EJERCICIO ACTUAL
        exercises = {
            "1": "neck_flexion_extension",
            "2": "neck_lateral_flexion", 
            "3": "neck_rotation"
        }
        
        current_exercise = "neck_flexion_extension"  # Por defecto
        
        # 📊 INFORMACIÓN DEL SISTEMA
        print(f"\n🦴 ANÁLISIS DE CUELLO CON GUÍA INTELIGENTE")
        print("=" * 60)
        print(f"🎯 Ejercicio actual: {current_exercise}")
        print("🔄 Controles:")
        print("   '1' → Flexión/Extensión (Vista SAGITAL ideal)")
        print("   '2' → Inclinación Lateral (Vista FRONTAL ideal)")
        print("   '3' → Rotación (Vista FRONTAL ideal)")
        print("   'r' → Reconfigurar cámara")
        print("   'd' → Diagnóstico de cámara")
        print("   'q' → Salir")
        print("=" * 60)
        print(f"📱 Cámara: {camera_info.get('probable_type', 'Desconocida')}")
        print(f"📐 Resolución: {camera_info.get('resolution', 'Desconocida')}")
        print("=" * 60)
        
        # 💡 CONSEJOS ESPECÍFICOS PARA CUELLO
        print("💡 CONSEJOS PARA ANÁLISIS DE CUELLO:")
        print("   📏 Mantén el torso quieto - solo mueve la cabeza")
        print("   🎯 Para flexión/extensión: ponte de PERFIL")
        print("   🎯 Para inclinación lateral: ponte de FRENTE")  
        print("   🔆 Asegúrate de que tu cara esté bien iluminada")
        print("=" * 60)
        
        fps_counter = 0
        fps_start = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Error: No se puede leer de la cámara")
                break
            
            # 🔄 VOLTEAR PARA EFECTO ESPEJO
            frame = cv2.flip(frame, 1)
            
            # 🎨 PROCESAR FRAME
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = analyzer.pose.process(rgb_frame)
            
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                
                # ✅ VERIFICAR PUNTOS REQUERIDOS
                if analyzer.check_required_points_visible(landmarks):
                    h, w, _ = frame.shape
                    
                    # 📐 ANÁLISIS DE ÁNGULOS
                    angles = analyzer.calculate_joint_angles(landmarks, (h, w))
                    
                    # 🧠 DEFINIR current_view PRIMERO
                    current_view = angles.get('orientation_info', {}).get('orientation', 'UNKNOWN')
                    
                    # DEBUG TEMPORAL:
                    angle_details = angles.get("angle_details", {})
                    if fps_counter % 30 == 0:  # Debug cada segundo
                        print(f"🔍 DEBUG ULTRA-DETALLADO:")
                        print(f"  Vista actual: {current_view}")
                        print(f"  Ángulo calculado: {angles.get('primary_angle', 0):.1f}°")
                        print(f"  Movimiento detectado: {angles.get('movement_direction', 'none')}")
                        print(f"  Desviación lateral: {angle_details.get('lateral_deviation', 0):.4f}")
                        print(f"  Desviación horizontal: {angle_details.get('horizontal_deviation', 0):.4f}")
                        print(f"  Distancia vertical: {angle_details.get('vertical_distance', 0):.4f}")
                        print(f"  Umbral mínimo: {angle_details.get('min_threshold', 0):.4f}")
                        print(f"  Ángulo crudo: {angle_details.get('raw_angle', 0):.1f}°")
                        print(f"  Movimiento detectado: {angle_details.get('movement_detected', False)}")
                        print(f"  Método: {angle_details.get('calculation_method', 'unknown')}")
                        print("-" * 60)
                    
                    # 🧠 GUÍA INTELIGENTE
                    guidance = exercise_guide.analyze_with_guidance(
                        current_exercise, current_view, angles, landmarks
                    )

                    # 🔍 DEBUG INFO (opcional - comentar si molesta)
                    orientation_info = angles.get('orientation_info', {})
                    if fps_counter % 30 == 0:  # Cada segundo aprox
                        print(f"🔍 Vista: {current_view} | Ángulo: {angles.get('primary_angle', 0):.1f}° | Ejercicio: {current_exercise}")
                    
                    # 🎨 VISUALIZACIÓN
                    frame = draw_neck_guidance(frame, guidance, angles)
                    frame = analyzer.draw_joint_visualization(frame, landmarks, angles)
                    
                    # 📊 INFORMACIÓN EN PANTALLA
                    draw_neck_info_panel(frame, angles, current_exercise)
                    
                else:
                    # ⚠️ PUNTOS NO VISIBLES
                    cv2.putText(frame, "AJUSTA POSICION - Cabeza no visible", 
                               (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    cv2.putText(frame, "Asegurate de que cara y hombros esten visibles", 
                               (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            else:
                # ❌ NO SE DETECTA POSE
                cv2.putText(frame, "NO POSE DETECTADA", 
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(frame, "Mejora iluminacion y posicion", 
                           (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            
            # 📊 FPS COUNTER
            fps_counter += 1
            if fps_counter % 30 == 0:
                fps_end = time.time()
                current_fps = 30 / (fps_end - fps_start)
                fps_start = fps_end
                cv2.putText(frame, f"FPS: {current_fps:.1f}", (frame.shape[1] - 100, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # 🎮 CONTROLES INFO
            exercise_name = {
                "neck_flexion_extension": "FLEXION/EXTENSION", 
                "neck_lateral_flexion": "INCLINACION LATERAL",
                "neck_rotation": "ROTACION"
            }.get(current_exercise, "DESCONOCIDO")
            
            cv2.putText(frame, f"EJERCICIO: {exercise_name} | 1=Flex/Ext 2=Lateral 3=Rotacion", 
                       (10, frame.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(frame, f"CAMARA: {camera_info.get('probable_type', 'Desconocida')} | r=Reconfig d=Diag q=Salir", 
                       (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            # 🖼️ MOSTRAR FRAME
            cv2.imshow('🦴 ANÁLISIS DE CUELLO + GUÍA INTELIGENTE', frame)
            
            # ⌨️ CONTROLES
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("👋 Saliendo del análisis de cuello...")
                break
            elif key == ord('1'):
                current_exercise = "neck_flexion_extension"
                print(f"🎯 Cambiado a: Flexión/Extensión de Cuello (Vista SAGITAL ideal)")
            elif key == ord('2'):
                current_exercise = "neck_lateral_flexion"
                print(f"🎯 Cambiado a: Inclinación Lateral de Cuello (Vista FRONTAL ideal)")
            elif key == ord('3'):
                current_exercise = "neck_rotation"
                print(f"🎯 Cambiado a: Rotación de Cuello (Vista FRONTAL ideal)")
            elif key == ord('r'):
                print("🔄 Reintentando configuración de cámara...")
                cap.release()
                camera_id, camera_info = auto_setup_camera_for_biomechanics()
                cap = cv2.VideoCapture(camera_id)
                print(f"✅ Cámara reconfigurada: {camera_info.get('probable_type', 'Desconocida')}")
            elif key == ord('d'):
                print("🔧 Iniciando diagnóstico de cámara...")
                diagnose_camera_problems()
            elif key == ord(' '):
                print("⏸️  Pausa - presiona cualquier tecla para continuar")
                cv2.waitKey(0)
        
        # 🧹 CLEANUP
        cap.release()
        cv2.destroyAllWindows()
        print("✅ Análisis de cuello completado")
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupción del usuario")
    except Exception as e:
        print(f"❌ Error durante el análisis: {e}")
        if 'cap' in locals():
            cap.release()
        cv2.destroyAllWindows()

def draw_neck_guidance(frame, guidance, angles):
    """🎯 Dibuja guía inteligente específica para cuello"""
    
    if not guidance.get("guidance_available", False):
        # Estado básico
        basic_status = guidance.get("basic_status", "")
        if basic_status:
            cv2.putText(frame, basic_status, (10, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 2)
        return frame
    
    view_guidance = guidance.get("view_guidance", {})
    y_pos = 130
    
    # 🎯 FONDO SEMI-TRANSPARENTE
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 125), (450, 240), (0, 0, 0), -1)
    frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
    
    # 📊 ESTADO DE VISTA
    status = view_guidance.get("current_view_status", "")
    status_color = {
        "OPTIMAL": (0, 255, 0),
        "VALIDATING": (0, 255, 255),
        "SUBOPTIMAL": (0, 165, 255)
    }.get(status, (255, 255, 255))
    
    cv2.putText(frame, f"VISTA: {status}", (10, y_pos), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
    y_pos += 25
    
    # 🎯 RECOMENDACIÓN
    next_action = guidance.get("next_recommendation", "")
    if next_action and len(next_action) > 0:
        cv2.putText(frame, f"RECOM: {next_action[:35]}", (10, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
        y_pos += 25
    
    # ⚠️ COMPENSACIONES
    compensations = guidance.get("predicted_compensations", [])
    if compensations:
        cv2.putText(frame, compensations[0][:40], (10, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        y_pos += 25
    
    # 📐 INFORMACIÓN DEL ÁNGULO
    maximized_analysis = guidance.get("maximized_analysis", {})
    primary_angle = maximized_analysis.get("primary_angle", 0)
    if primary_angle > 0:
        frame = draw_text_with_pil(frame, f"ANGULO: {primary_angle:.1f}°", (10, y_pos), 16, (255, 255, 255))
        y_pos += 20
    
    # 📊 EVALUACIÓN CLÍNICA
    assessment = angles.get("assessment", {})
    if assessment.get("status"):
        status_text = assessment["status"]
        percentage = assessment.get("percentage", 0)
        
        assessment_color = {
            "EXCELLENT": (0, 255, 0),
            "GOOD": (0, 255, 255),
            "FAIR": (0, 165, 255),
            "INSUFFICIENT": (0, 0, 255)
        }.get(status_text, (255, 255, 255))
        
        cv2.putText(frame, f"EVAL: {status_text} ({percentage:.0f}%)", (10, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, assessment_color, 1)
    
    return frame

def draw_neck_info_panel(frame, angles, current_exercise):
    """📊 Panel de información específico para cuello"""
    
    # Panel en esquina superior derecha
    panel_x = frame.shape[1] - 250
    panel_y = 40
    
    overlay = frame.copy()
    cv2.rectangle(overlay, (panel_x - 10, panel_y - 10), 
                  (frame.shape[1] - 10, panel_y + 120), (0, 0, 0), -1)
    frame = cv2.addWeighted(frame, 0.8, overlay, 0.2, 0)
    
    # Información del ejercicio
    exercise_names = {
        "neck_flexion_extension": "Flexión/Extensión",
        "neck_lateral_flexion": "Inclinación Lateral", 
        "neck_rotation": "Rotación"
    }
    
    exercise_name = exercise_names.get(current_exercise, "Desconocido")
    cv2.putText(frame, f"CUELLO: {exercise_name}", (panel_x, panel_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Dirección del movimiento
    movement_dir = angles.get("movement_direction", "neutral")
    if movement_dir != "neutral":
        panel_y += 25
        cv2.putText(frame, f"Direccion: {movement_dir}", (panel_x, panel_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    
    # Calidad del análisis
    quality = angles.get("analysis_quality", "UNKNOWN")
    quality_color = {
        "HIGH": (0, 255, 0),
        "MEDIUM": (0, 255, 255),
        "LOW": (0, 165, 255)
    }.get(quality, (255, 255, 255))
    
    panel_y += 25
    cv2.putText(frame, f"Calidad: {quality}", (panel_x, panel_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, quality_color, 1)
    
    # Vista óptima
    optimal_view = angles.get("optimal_view", "")
    current_orientation = angles.get("orientation_info", {}).get("orientation", "")
    
    if optimal_view and optimal_view != current_orientation:
        panel_y += 25
        cv2.putText(frame, f"Opt: {optimal_view}", (panel_x, panel_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
    
    return frame

if __name__ == "__main__":
    main()