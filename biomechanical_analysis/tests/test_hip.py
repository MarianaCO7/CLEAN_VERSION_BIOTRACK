"""
🦴 TEST DE CADERA CON SMART CAMERA MANAGER
🎯 Análisis completo de flexión/extensión de cadera
📐 Medición científicamente válida para fines educativos
🏥 Evaluación clínica con rangos normativos
"""

import sys
import os

# Configuración de paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from joints.hip_analyzer import HipAnalyzer
from core.camera_manager import auto_setup_camera_for_biomechanics
import cv2
import time

def main():
    """🚀 TEST COMPLETO DE ANÁLISIS DE CADERA"""
    
    print("=" * 60)
    print("🦴 SISTEMA DE ANÁLISIS BIOMECÁNICO - TEST CADERA")
    print("🎯 OBJETIVO: Medición precisa de ángulos de cadera")
    print("🏥 EVALUACIÓN: Rangos normativos y recomendaciones clínicas")  
    print("🎓 PROPÓSITO: Educativo - Aprendizaje de biomecánica")
    print("=" * 60)
    print()
    
    # 🎯 INFORMACIÓN EDUCATIVA DE CADERA
    print("📚 INFORMACIÓN BIOMECÁNICA DE CADERA:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🦴 ARTICULACIÓN: Cadera (Coxofemoral)")
    print("📐 ÁNGULO MEDIDO: Cadera-Rodilla-Tobillo")  
    print("🏥 RANGOS NORMALES:")
    print("   • FLEXIÓN: 0° - 120° (Funcional: 90°)")
    print("   • EXTENSIÓN: 0° - 30° (Funcional: 20°)")
    print("   • NEUTRAL: ~180° (pierna recta)")
    print("🎯 MOVIMIENTOS ANALIZADOS:")
    print("   • Vista FRONTAL: Ambas caderas simultáneamente")
    print("   • Vista SAGITAL: Enfoque en cadera visible")
    print("   • Flexión hacia adelante (reducción de ángulo)")
    print("   • Extensión hacia atrás (aumento de ángulo)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    
    # 🚀 INICIALIZAR SISTEMA
    print("🎯 PRUEBA AVANZADA: FLEXIÓN/EXTENSIÓN DE CADERA + FILTRO")
    
    try:
        # 🎯 SETUP CON FALLBACK AUTOMÁTICO (igual que test_shoulder.py)
        camera_id, camera_info = auto_setup_camera_for_biomechanics()
        
        analyzer = HipAnalyzer()
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
        print("   • Colócate de pie con piernas visibles completas")
        print("   • FRONTAL: Ambas caderas, mueve una pierna") 
        print("   • SAGITAL: De perfil, flexiona/extiende cadera visible")
        print("   • Mejora la iluminación si es posible")
        print("❌ Presiona 'q' para salir")
        print("=" * 60)
        
        # 🎯 VARIABLES DE CONTROL
        fps_counter = 0
        fps_start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ ERROR: No se puede leer el frame de la cámara")
                break
            
            # 🪞 ESPEJO para naturalidad
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            
            # 🦴 DETECCIÓN DE POSE Y ANÁLISIS
            landmarks = analyzer.detect_pose(frame)
            
            if landmarks and analyzer.check_required_points_visible(landmarks):
                # 📐 CALCULAR ÁNGULOS DE CADERA
                angles = analyzer.calculate_joint_angles(landmarks, (h, w))
                
                # 🎨 VISUALIZACIÓN COMPLETA
                frame = analyzer.draw_joint_visualization(frame, landmarks, angles)
                
                # 📊 INFORMACIÓN ADICIONAL EN CONSOLA (cada 30 frames)
                if fps_counter % 30 == 0:
                    print(f"📐 CADERA DER: {angles['right_hip']:.1f}° | CADERA IZQ: {angles['left_hip']:.1f}°")
                    
                    # 🏥 EVALUACIÓN CLÍNICA EDUCATIVA
                    orientation = angles.get('orientation_info', {}).get('orientation', 'UNKNOWN')
                    primary_leg = angles.get('primary_leg', 'BOTH')
                    
                    if angles['right_hip'] > 0 or angles['left_hip'] > 0:
                        print(f"🧭 Vista: {orientation} | Enfoque: {primary_leg}")
                        
                        # Análisis educativo simple
                        for side, angle in [('DERECHA', angles['right_hip']), ('IZQUIERDA', angles['left_hip'])]:
                            if angle > 0:
                                if angle > 160:
                                    movement = "EXTENSIÓN" if angle > 180 else "NEUTRAL"
                                    status = "EXCELENTE" if angle > 175 else "BUENO"
                                elif angle < 140:
                                    movement = "FLEXIÓN MODERADA"
                                    status = "FUNCIONAL"
                                elif angle < 90:
                                    movement = "FLEXIÓN MÁXIMA"  
                                    status = "RANGO COMPLETO"
                                else:
                                    movement = "FLEXIÓN LEVE"
                                    status = "NORMAL"
                                
                                print(f"  🦴 CADERA {side}: {movement} - {status}")
                
            else:
                # 📍 GUÍA VISUAL CUANDO NO HAY DETECCIÓN
                cv2.putText(frame, "POSICIONATE PARA VER PIERNAS COMPLETAS", 
                           (50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(frame, "Cadera - Rodilla - Tobillo deben ser visibles", 
                           (50, h//2 + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # 🎯 INDICACIONES POR ORIENTACIÓN
                cv2.putText(frame, "FRONTAL: Ambas piernas | SAGITAL: De perfil", 
                           (50, h//2 + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 100), 1)
            
            # 📊 FPS COUNTER
            fps_counter += 1
            if fps_counter % 30 == 0:
                fps_end_time = time.time()
                fps = 30 / (fps_end_time - fps_start_time)
                fps_start_time = fps_end_time
            
            # 📺 MOSTRAR RESULTADO
            cv2.imshow("🦴 ANÁLISIS BIOMECÁNICO - CADERA", frame)
            
            # ⌨️ CONTROL DE SALIDA
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # 'q' o ESC
                break
            elif key == ord('r'):  # 'r' para reset de filtros
                analyzer.reset_filters()
                print("🔄 Filtros temporales reiniciados")
            elif key == ord('i'):  # 'i' para información
                print("\n📚 INFORMACIÓN DE USO:")
                print("  🦴 CADERA: Ángulo entre cadera-rodilla-tobillo")
                print("  🏥 NORMAL: ~180° (pierna recta)")
                print("  📐 FLEXIÓN: < 140° (rodilla hacia pecho)")
                print("  📐 EXTENSIÓN: > 180° (pierna hacia atrás)")
                print("  🧭 FRONTAL: Ve ambas caderas")
                print("  🧭 SAGITAL: Enfoque en cadera visible")
                print("  ⌨️  'r' = Reset filtros | 'i' = Info | 'q' = Salir\n")
    
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        print("🔧 Verifica que:")
        print("  • La cámara esté conectada y funcionando")
        print("  • No haya otras aplicaciones usando la cámara")
        print("  • Los drivers de cámara estén actualizados")
    
    finally:
        # 🧹 LIMPIEZA
        try:
            cap.release()
        except:
            pass
        cv2.destroyAllWindows()
        
        print("\n" + "=" * 60)
        print("🎓 ANÁLISIS DE CADERA COMPLETADO")
        print("📚 OBJETIVOS EDUCATIVOS CUMPLIDOS:")
        print("  ✅ Medición precisa de ángulos articulares") 
        print("  ✅ Comprensión de rangos normativos")
        print("  ✅ Visualización de patrones de movimiento")
        print("  ✅ Evaluación funcional básica")
        print("🦴 Conocimiento biomecánico adquirido: CADERA")
        print("=" * 60)

if __name__ == "__main__":
    main()