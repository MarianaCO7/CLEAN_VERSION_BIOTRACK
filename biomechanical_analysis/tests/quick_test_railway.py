"""
🚀 QUICK START - Test Railway Simplificado
═══════════════════════════════════════════

Script minimalista para pruebas rápidas con Railway.
Versión simplificada de test_shoulder_railway.py

USO RÁPIDO:
-----------
python quick_test_railway.py

El script te pedirá:
1. URL de Railway
2. Ejercicio a probar

Luego se conecta automáticamente.
"""

import cv2
import requests
import base64
import time
from datetime import datetime

def main():
    print("\n" + "="*60)
    print("🚂 QUICK TEST - RAILWAY CONNECTION")
    print("="*60 + "\n")
    
    # 1. Pedir URL
    railway_url = input("📝 URL de Railway (ej: https://tu-app.railway.app): ").strip()
    
    if not railway_url:
        print("❌ Error: URL requerida")
        return
    
    railway_url = railway_url.rstrip('/')
    
    # 2. Pedir ejercicio
    print("\n📋 Ejercicios disponibles:")
    print("   1. flexion")
    print("   2. abduction")
    print("   3. extension")
    print("   4. external_rotation")
    
    exercise_choice = input("\n🎯 Selecciona ejercicio (1-4): ").strip()
    
    exercises = {
        '1': 'flexion',
        '2': 'abduction',
        '3': 'extension',
        '4': 'external_rotation'
    }
    
    exercise = exercises.get(exercise_choice, 'flexion')
    
    print(f"\n✅ Ejercicio seleccionado: {exercise}")
    
    # 3. Test de conexión
    print(f"\n🔍 Probando conexión con {railway_url}...")
    
    try:
        response = requests.get(railway_url, timeout=5)
        if response.status_code == 200:
            print("✅ Conexión exitosa!")
        else:
            print(f"⚠️  Advertencia: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        return
    
    # 4. Configurar ejercicio
    print(f"\n⚙️  Configurando ejercicio en Railway...")
    
    try:
        response = requests.post(
            f"{railway_url}/api/set_exercise",
            json={'joint': 'shoulder', 'exercise': exercise},
            timeout=5
        )
        if response.status_code == 200:
            print("✅ Ejercicio configurado")
        else:
            print("⚠️  No se pudo configurar (continuando de todos modos)")
    except:
        print("⚠️  Endpoint no disponible (continuando de todos modos)")
    
    # 5. Abrir cámara
    print("\n📹 Abriendo cámara...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ No se pudo abrir la cámara")
        return
    
    print("✅ Cámara abierta")
    
    # Configurar resolución
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("\n" + "="*60)
    print("🎬 STREAMING INICIADO")
    print("="*60)
    print("📋 INSTRUCCIONES:")
    
    if exercise == 'flexion':
        print("   • Ponte de PERFIL a la cámara")
        print("   • Levanta el brazo hacia ADELANTE")
    elif exercise == 'abduction':
        print("   • Ponte de FRENTE a la cámara")
        print("   • Levanta el brazo hacia el LADO")
    elif exercise == 'extension':
        print("   • Ponte de PERFIL a la cámara")
        print("   • Lleva el brazo hacia ATRÁS")
    else:
        print("   • Ponte de FRENTE a la cámara")
        print("   • Rota el hombro")
    
    print("\n⌨️  Presiona 'Q' para salir\n")
    
    # 6. Loop de streaming
    session = requests.Session()
    frame_count = 0
    success_count = 0
    start_time = time.time()
    last_angle = None
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                continue
            
            frame_count += 1
            frame = cv2.flip(frame, 1)
            
            # Enviar cada 3 frames
            if frame_count % 3 == 0:
                try:
                    # Codificar
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    frame_b64 = base64.b64encode(buffer).decode('utf-8')
                    
                    # Enviar
                    response = session.post(
                        f"{railway_url}/api/receive_frame",
                        json={
                            'frame': f'data:image/jpeg;base64,{frame_b64}',
                            'timestamp': time.time(),
                            'metadata': {'exercise': exercise, 'joint': 'shoulder'}
                        },
                        timeout=1
                    )
                    
                    if response.status_code == 200:
                        success_count += 1
                        
                        # Intentar extraer ángulo
                        try:
                            data = response.json()
                            if 'angle' in data:
                                last_angle = data['angle']
                        except:
                            pass
                
                except:
                    pass
            
            # Mostrar frame con info
            display_frame = frame.copy()
            
            # Estadísticas
            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0
            success_rate = (success_count / (frame_count // 3) * 100) if frame_count > 0 else 0
            
            cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.putText(display_frame, f"Enviados: {frame_count // 3} | OK: {success_count}",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.putText(display_frame, f"Tasa: {success_rate:.0f}%", (10, 85),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            if last_angle:
                cv2.putText(display_frame, f"Angulo: {last_angle:.1f} deg", (10, 115),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            cv2.imshow('Quick Test Railway - Presiona Q', display_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        pass
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        
        # Reporte
        elapsed = time.time() - start_time
        print("\n" + "="*60)
        print("📊 RESUMEN")
        print("="*60)
        print(f"⏱️  Duración: {elapsed:.1f}s")
        print(f"📤 Frames enviados: {frame_count // 3}")
        print(f"✅ Frames exitosos: {success_count}")
        print(f"📈 Tasa de éxito: {success_rate:.1f}%")
        
        if last_angle:
            print(f"📐 Último ángulo: {last_angle:.1f}°")
        
        print("\n✨ Test completado\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")
