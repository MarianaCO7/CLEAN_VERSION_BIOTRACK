"""
Tests Module
Migración de tests individuales
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from joints.elbow_analyzer import ElbowAnalyzer
from core.camera_manager import auto_setup_camera_for_biomechanics  # 🆕
import cv2

def main():
    """
    🎯 TEST DE CODO CON SETUP AUTOMÁTICO
    📋 TU FUNCIONALIDAD EXACTA + mejoras automáticas
    """
    
    # 🎯 SETUP AUTOMÁTICO DE CÁMARA
    camera_id, camera_info = auto_setup_camera_for_biomechanics()
    
    analyzer = ElbowAnalyzer()
    cap = cv2.VideoCapture(camera_id)  # 🆕 Automático
    
    # 🔄 TUS MENSAJES ACTUALIZADOS
    print(f"\n🎯 PRUEBA AVANZADA: FLEXIÓN DE CODO + FILTRO")
    print(f"📱 CÁMARA: ID {camera_id} (Detectada automáticamente)")
    print(f"📐 Tipo: {camera_info.get('probable_type', 'Desconocida')}")
    print("🪞 VISTA: Como espejo (más natural)")
    print("📐 ÁNGULOS: Con símbolos Unicode correctos")
    print("🔧 FILTRO: Temporal para suavizar")
    print("🧠 ORIENTACIÓN: Detección automática de plano")
    print("💡 TIP: Mejora la iluminación si es posible")
    print("❌ Presiona 'q' para salir")
    print("=" * 60)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"❌ Error leyendo cámara {camera_id}")
            break
        
        # 🔄 TU LÓGICA EXACTA - SIN CAMBIOS
        frame = cv2.flip(frame, 1)  # Vista espejo
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = analyzer.pose.process(rgb_frame)
        
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            
            # TU VALIDACIÓN EXACTA
            if analyzer.check_required_points_visible(landmarks):
                h, w, _ = frame.shape
                
                # USAR EL ANALIZADOR (en lugar de lógica directa)
                angles = analyzer.calculate_joint_angles(landmarks, (h, w))
                frame = analyzer.draw_joint_visualization(frame, landmarks, angles)
                
            else:
                # TUS MENSAJES DE ERROR EXACTOS
                cv2.putText(frame, "PUNTOS NO VISIBLES - Mejora iluminacion", 
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        else:
            cv2.putText(frame, "NO POSE DETECTADA", 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # 🆕 TU INFORMACIÓN INFERIOR ACTUALIZADA
        cv2.putText(frame, f"SMART CAM {camera_id} | Orientacion + Arcos = Angulos | q = salir", 
                   (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # TU VENTANA EXACTA
        cv2.imshow('TEST CODO + SMART CAMERA: Análisis Biomecánico', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print(f"✅ Prueba de codo completada con cámara {camera_id}")

if __name__ == "__main__":
    main()