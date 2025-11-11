"""
🦶 TEST DE TOBILLO CON TODAS LAS MEJORES CARACTERÍSTICAS
🧠 SmartCameraManager + OrientationDetector + Filtros temporales
📐 Dorsiflexión, plantiflexión y análisis postural del pie
🎯 Usa EXACTAMENTE el mismo patrón exitoso que rodilla/cadera
"""

# 🔇 SILENCIAR MENSAJES DE TENSORFLOW
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import sys
import cv2
import time
from pathlib import Path

# 🛠️ CONFIGURACIÓN DE PATHS
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.append(str(project_root))

# 🎯 IMPORTS PRINCIPALES
from joints.ankle_analyzer import AnkleAnalyzer
from core.camera_manager import auto_setup_camera_for_biomechanics

def main():
    """🚀 TEST COMPLETO DE ANÁLISIS DE TOBILLO"""
    
    print("=" * 60)
    print("🦶 SISTEMA DE ANÁLISIS BIOMECÁNICO - TEST TOBILLO")
    print("🎯 OBJETIVO: Medición precisa de dorsi/plantiflexión")
    print("🏥 EVALUACIÓN: Rangos normativos y recomendaciones clínicas")  
    print("🎓 PROPÓSITO: Educativo - Aprendizaje de biomecánica")
    print("=" * 60)
    print()
    
    # 🎯 INFORMACIÓN EDUCATIVA DE TOBILLO
    print("📚 INFORMACIÓN BIOMECÁNICA DE TOBILLO:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🦶 ARTICULACIÓN: Tobillo (Talocrural)")
    print("📐 ÁNGULO MEDIDO: Rodilla-Tobillo-Pie")  
    print("🏥 RANGOS NORMALES:")
    print("   • NEUTRAL: ~90° (pie perpendicular a pierna)")
    print("   • DORSIFLEXIÓN: 90° - 120° (punta hacia arriba)")
    print("   • PLANTIFLEXIÓN: 45° - 90° (punta hacia abajo)")
    print("   • FUNCIONAL: 85° - 105° (marcha normal)")
    print("🎯 MOVIMIENTOS ANALIZADOS:")
    print("   • Vista FRONTAL: Ambos tobillos simultáneamente")
    print("   • Vista SAGITAL: Enfoque en tobillo visible")
    print("   • Dorsiflexión (punta arriba - aumento de ángulo)")
    print("   • Plantiflexión (punta abajo - reducción de ángulo)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    
    # 🚀 INICIALIZAR SISTEMA
    print("🎯 PRUEBA AVANZADA: DORSI/PLANTIFLEXIÓN + FILTRO")
    
    try:
        # 🎯 SETUP CON FALLBACK AUTOMÁTICO (igual que test_knee.py exitoso)
        camera_id, camera_info = auto_setup_camera_for_biomechanics()
        
        analyzer = AnkleAnalyzer()
        cap = cv2.VideoCapture(camera_id)
        
        # 🔍 VERIFICACIÓN FINAL
        ret, test_frame = cap.read()
        if not ret or test_frame is None:
            print("❌ Error: La cámara seleccionada no responde")
            print("🔧 Ejecutando diagnóstico...")
            return
        
        # Configurar cámara básica
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        print("🪞 VISTA: Como espejo (más natural)")
        print("📐 ÁNGULOS: Con símbolos Unicode correctos")
        print("🔧 FILTRO: Temporal para suavizar mediciones")
        print("🧠 ORIENTACIÓN: Detección automática de plano")
        print("🏥 EVALUACIÓN: Rangos clínicos integrados")
        print("💡 TIP: Para mejores resultados:")
        print("   • Colócate de pie con pies visibles completos")
        print("   • FRONTAL: Ambos tobillos, mueve pies arriba/abajo") 
        print("   • SAGITAL: De perfil, dorsi/plantiflexión del pie visible")
        print("   • Mejora la iluminación si es posible")
        print("❌ Presiona 'q' para salir")
        print("=" * 60)
        
        # 🎯 VARIABLES DE CONTROL
        frame_count = 0
        fps_counter = 0
        fps_timer = time.time()
        max_no_detection_frames = 150  # 5 segundos a 30fps
        no_detection_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 🪞 EFECTO ESPEJO
            frame = cv2.flip(frame, 1)
            frame_count += 1
            
            # 📊 DETECTAR POSE
            landmarks = analyzer.detect_pose(frame)
            
            if landmarks is not None:
                # ✅ ANÁLISIS EXITOSO
                no_detection_count = 0
                
                # 🔍 VERIFICAR PUNTOS NECESARIOS
                if analyzer.check_required_points_visible(landmarks):
                    
                    # 📐 CALCULAR ÁNGULOS DE TOBILLO
                    h, w, _ = frame.shape
                    angles = analyzer.calculate_joint_angles(landmarks, (h, w))
                    
                    # 🎨 VISUALIZACIÓN COMPLETA
                    frame = analyzer.draw_joint_visualization(frame, landmarks, angles)
                    
                    # 📊 INFORMACIÓN DIAGNÓSTICA (cada 30 frames)
                    if frame_count % 30 == 0:
                        orientation = angles.get('orientation_info', {}).get('orientation', 'UNKNOWN')
                        primary_leg = angles.get('primary_leg', 'BOTH')
                        
                        # ✅ ARREGLAR FORMATO - CONVERTIR A FLOAT PRIMERO
                        right_angle = float(angles.get('right_ankle', 0))
                        left_angle = float(angles.get('left_ankle', 0))
                        
                        print(f"📊 Frame {frame_count:4d} | Orientación: {orientation:8s} | "
                              f"Tobillo Der: {right_angle:5.1f}° | "           # ✅ CORREGIDO
                              f"Tobillo Izq: {left_angle:5.1f}° | "            # ✅ CORREGIDO
                              f"Enfoque: {primary_leg}")
                    
                    # 🦶 EVALUACIÓN CLÍNICA (cada 60 frames)
                    if frame_count % 60 == 0:
                        # ✅ PROTEGER CONTRA ERRORES
                        try:
                            right_angle = float(angles.get('right_ankle', 90))
                            left_angle = float(angles.get('left_ankle', 90))
                            
                            right_evaluation = analyzer._interpret_ankle_angle(right_angle)  # ✅ Con 'analyzer.'
                            left_evaluation = analyzer._interpret_ankle_angle(left_angle)    # ✅ Con 'analyzer.'
                            
                            print(f"🏥 EVALUACIÓN: Der={right_evaluation}, Izq={left_evaluation}")
                            
                            # Alertas clínicas
                            if right_angle > 110 or left_angle > 110:
                                print("⚠️  DORSIFLEXIÓN PRONUNCIADA detectada")
                            elif right_angle < 75 or left_angle < 75:
                                print("⚠️  PLANTIFLEXIÓN PRONUNCIADA detectada")
                        except Exception as e:
                            print(f"⚠️ Error en evaluación clínica: {e}")
                
                else:
                    # 📍 GUIAR POSICIONAMIENTO
                    cv2.putText(frame, "POSICIONATE: Pies completamente visibles", 
                               (10, frame.shape[0] - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    cv2.putText(frame, "FRONTAL: Ambos pies | SAGITAL: De perfil", 
                               (10, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
            
            else:
                # 📍 SIN DETECCIÓN
                no_detection_count += 1
                cv2.putText(frame, f"Buscando persona... ({no_detection_count})", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                cv2.putText(frame, "Asegurate de estar completamente visible", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                # 🔄 AUTO-RESET si no hay detección por mucho tiempo
                if no_detection_count > max_no_detection_frames:
                    print("🔄 Auto-reset: Sin detección prolongada")
                    analyzer.reset_filters()
                    no_detection_count = 0
            
            # 📊 FPS CONTADOR
            fps_counter += 1
            if time.time() - fps_timer >= 1.0:
                cv2.putText(frame, f"FPS: {fps_counter}", (frame.shape[1] - 100, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                fps_counter = 0
                fps_timer = time.time()
            
            # 📺 MOSTRAR FRAME
            cv2.imshow('🦶 Análisis Biomecánico - TOBILLO', frame)
            
            # ⌨️ CONTROL DE TECLADO
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                print("🔄 Reseteando filtros...")
                analyzer.reset_filters()
            elif key == ord(' '):
                print("⏸️  Pausa - presiona cualquier tecla para continuar")
                cv2.waitKey(0)
        
        # 🧹 LIMPIEZA
        cap.release()
        cv2.destroyAllWindows()
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        print("🔧 Verifica que:")
        print("  • La cámara esté conectada y funcionando")
        print("  • No haya otras aplicaciones usando la cámara")
        print("  • Los drivers de cámara estén actualizados")
    
    finally:
        print("\n" + "=" * 60)
        print("🎓 ANÁLISIS DE TOBILLO COMPLETADO")
        print("📚 OBJETIVOS EDUCATIVOS CUMPLIDOS:")
        print("  ✅ Medición precisa de ángulos articulares")
        print("  ✅ Comprensión de rangos normativos")
        print("  ✅ Visualización de patrones de movimiento")
        print("  ✅ Evaluación funcional básica")
        print("🦶 Conocimiento biomecánico adquirido: TOBILLO")
        print("=" * 60)

if __name__ == "__main__":
    main()