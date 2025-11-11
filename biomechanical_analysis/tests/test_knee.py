"""
🦵 TEST DE RODILLA CON TODAS LAS MEJORES CARACTERÍSTICAS
🧠 SmartCameraManager + OrientationDetector + Filtros temporales
"""

# 🔇 SILENCIAR MENSAJES DE TENSORFLOW
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from joints.knee_analyzer import KneeAnalyzer
from core.camera_manager import auto_setup_camera_for_biomechanics, diagnose_camera_problems
import cv2

def main():
    """
    🦵 TEST COMPLETO DE RODILLA
    🎯 Incorpora TODAS las mejores prácticas del proyecto
    """
    
    try:
        # 🎯 SETUP AUTOMÁTICO DE CÁMARA
        camera_id, camera_info = auto_setup_camera_for_biomechanics()
        
        analyzer = KneeAnalyzer()
        cap = cv2.VideoCapture(camera_id)
        
        # 🔍 VERIFICACIÓN FINAL
        ret, test_frame = cap.read()
        if not ret or test_frame is None:
            print("❌ Error: La cámara seleccionada no responde")
            print("🔧 Ejecutando diagnóstico...")
            diagnose_camera_problems()
            return
        
        # 🔄 INFORMACIÓN COMPLETA
        print(f"\n🦵 ANÁLISIS DE RODILLA - CÁMARA {camera_id}")
        print(f"📱 Tipo: {camera_info.get('probable_type', 'Desconocida')}")
        print(f"📐 Resolución: {camera_info.get('resolution', 'Desconocida')}")
        print("=" * 60)
        print("🦵 MEDICIONES: Flexión de rodillas + separación")
        print("🧠 ORIENTACIÓN: Detección automática de plano")
        print("🔄 FILTROS: Suavizado temporal automático")
        print("💡 TIP: Haz sentadillas o flexiones de rodilla")
        print("🎯 POSICIÓN: Aléjate para mostrar piernas completas")
        print("❌ Presiona 'q' para salir")
        print("=" * 60)
        
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print(f"❌ Error leyendo cámara {camera_id}")
                break
            
            frame_count += 1
            
            # 🔍 DETECTAR FRAMES NEGROS
            if frame_count > 30:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                mean_brightness = cv2.mean(gray)[0]
                
                if mean_brightness < 10:
                    cv2.putText(frame, "FRAME NEGRO - Verifica configuracion camara", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            # 🪞 VISTA ESPEJO (patrón exitoso)
            frame = cv2.flip(frame, 1)
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = analyzer.pose.process(rgb_frame)
            
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                
                if analyzer.check_required_points_visible(landmarks):
                    h, w, _ = frame.shape
                    
                    # 🦵 ANÁLISIS COMPLETO DE RODILLA
                    angles = analyzer.calculate_joint_angles(landmarks, (h, w))
                    frame = analyzer.draw_joint_visualization(frame, landmarks, angles)
                    
                else:
                    cv2.putText(frame, "PIERNAS NO VISIBLES - Alejate mas de la camara", 
                               (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            else:
                cv2.putText(frame, "NO POSE DETECTADA", 
                           (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # 🆕 INFO DE CÁMARA Y CONTROLES
            cv2.putText(frame, f"SMART CAM {camera_id} | Analisis Completo Rodilla | q = salir", 
                       (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            cv2.imshow('TEST RODILLA: Análisis Biomecánico Completo', frame)
            
            # 🎮 CONTROLES
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('d'):
                print("🔧 Ejecutando diagnóstico de cámaras...")
                cap.release()
                cv2.destroyAllWindows()
                diagnose_camera_problems()
                input("\nPresiona ENTER para continuar...")
                cap = cv2.VideoCapture(camera_id)
        
        cap.release()
        cv2.destroyAllWindows()
        print(f"✅ Prueba de rodilla completada con cámara {camera_id}")
        
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        print("🔧 Ejecutando diagnóstico...")
        diagnose_camera_problems()

if __name__ == "__main__":
    main()