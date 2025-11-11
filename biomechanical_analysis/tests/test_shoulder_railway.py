"""
🚂 TEST DE HOMBRO CON RAILWAY - STREAMING EN TIEMPO REAL
═══════════════════════════════════════════════════════════

Este script conecta tu cámara LOCAL con el servidor RAILWAY para:
1. 📹 Capturar frames de tu cámara física
2. 🚀 Enviarlos a Railway vía HTTP
3. 🧠 Railway procesa con MediaPipe y calcula ángulos
4. 📊 Recibir resultados en tiempo real
5. 🖼️ Mostrar visualización en tu pantalla

ARQUITECTURA:
-------------
    🏠 Tu Laptop                        ☁️ Railway
    ┌─────────────┐                    ┌──────────────┐
    │ 📹 Webcam   │                    │ 🐍 Flask     │
    │     ↓       │ ── HTTP POST ────> │ 🧠 MediaPipe │
    │ 📤 Envía    │    (base64)        │ 📐 Analyzer  │
    │   frames    │                    │     ↓        │
    │     ↓       │ <── HTTP GET ─────  │ 🎨 Procesa  │
    │ 📥 Recibe   │    (JPEG)          │     ↓        │
    │   procesado │                    │ 📊 Resultados│
    │     ↓       │                    └──────────────┘
    │ 🖼️ Muestra  │
    └─────────────┘

USO:
----
# 1. Configurar URL de Railway
export RAILWAY_URL="https://tu-app.railway.app"

# 2. Ejecutar test
python test_shoulder_railway.py --exercise flexion --duration 60

# 3. Ejecutar con URL directa
python test_shoulder_railway.py --url https://tu-app.railway.app --exercise flexion
"""

import sys
import os
import cv2
import numpy as np
import requests
import base64
import time
import argparse
from datetime import datetime
import json
from threading import Thread, Lock
import queue

# 🎨 Colores para terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Imprime un encabezado bonito"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def print_success(text):
    """Imprime mensaje de éxito"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    """Imprime mensaje de error"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_info(text):
    """Imprime información"""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def print_warning(text):
    """Imprime advertencia"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


class RailwayStreamingClient:
    """
    Cliente para streaming bidireccional con Railway
    - Envía frames de cámara local a Railway
    - Recibe frames procesados desde Railway
    - Mide latencia y performance
    """
    
    def __init__(self, railway_url, exercise_type='flexion'):
        """
        Args:
            railway_url: URL base de tu app en Railway (ej: https://tu-app.railway.app)
            exercise_type: Tipo de ejercicio (flexion, abduction, etc.)
        """
        self.railway_url = railway_url.rstrip('/')
        self.exercise_type = exercise_type
        self.session = requests.Session()
        
        # Estadísticas
        self.stats = {
            'frames_sent': 0,
            'frames_received': 0,
            'frames_failed': 0,
            'total_latency': 0,
            'max_latency': 0,
            'min_latency': float('inf'),
            'angles_received': 0,
            'max_angle': 0,
            'min_angle': 180,
            'start_time': None
        }
        
        # Thread-safe queue para frames procesados
        self.processed_frame_queue = queue.Queue(maxsize=5)
        self.latest_angle = None
        self.latest_metadata = {}
        self.lock = Lock()
        
        # Control de threads
        self.running = False
        self.send_thread = None
        self.receive_thread = None
        
        print_info(f"Cliente inicializado para: {self.railway_url}")
        print_info(f"Ejercicio: {self.exercise_type}")
    
    def test_connection(self):
        """Verifica que Railway esté accesible"""
        print_info("Probando conexión con Railway...")
        
        try:
            response = self.session.get(f"{self.railway_url}/", timeout=10)
            if response.status_code == 200:
                print_success(f"Conexión exitosa - Status: {response.status_code}")
                return True
            else:
                print_error(f"Conexión fallida - Status: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print_error("No se pudo conectar a Railway. Verifica la URL.")
            return False
        except requests.exceptions.Timeout:
            print_error("Timeout - Railway no responde.")
            return False
        except Exception as e:
            print_error(f"Error de conexión: {str(e)}")
            return False
    
    def set_exercise(self):
        """Configura el ejercicio en Railway"""
        print_info(f"Configurando ejercicio en Railway: {self.exercise_type}...")
        
        try:
            response = self.session.post(
                f"{self.railway_url}/api/set_exercise",
                json={
                    'joint': 'shoulder',
                    'exercise': self.exercise_type
                },
                timeout=5
            )
            
            if response.status_code == 200:
                print_success(f"Ejercicio configurado: {self.exercise_type}")
                return True
            else:
                print_error(f"Error configurando ejercicio: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Error al configurar ejercicio: {str(e)}")
            return False
    
    def encode_frame(self, frame):
        """Codifica frame a base64 para envío"""
        try:
            # Redimensionar para reducir tamaño (opcional)
            # frame = cv2.resize(frame, (640, 480))
            
            # Codificar a JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            # Convertir a base64
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return f"data:image/jpeg;base64,{frame_base64}"
        except Exception as e:
            print_error(f"Error codificando frame: {str(e)}")
            return None
    
    def send_frame(self, frame):
        """Envía un frame a Railway para procesamiento"""
        frame_base64 = self.encode_frame(frame)
        
        if not frame_base64:
            return False
        
        try:
            send_time = time.time()
            
            response = self.session.post(
                f"{self.railway_url}/api/receive_frame",
                json={
                    'frame': frame_base64,
                    'timestamp': send_time,
                    'metadata': {
                        'exercise': self.exercise_type,
                        'client': 'test_railway'
                    }
                },
                timeout=2  # 2 segundos de timeout
            )
            
            latency = (time.time() - send_time) * 1000  # en ms
            
            if response.status_code == 200:
                self.stats['frames_sent'] += 1
                self.stats['total_latency'] += latency
                self.stats['max_latency'] = max(self.stats['max_latency'], latency)
                self.stats['min_latency'] = min(self.stats['min_latency'], latency)
                
                # Guardar metadata (ángulos, etc.)
                data = response.json()
                if 'angle' in data:
                    with self.lock:
                        self.latest_angle = data['angle']
                        self.latest_metadata = data
                        self.stats['angles_received'] += 1
                        self.stats['max_angle'] = max(self.stats['max_angle'], data['angle'])
                        self.stats['min_angle'] = min(self.stats['min_angle'], data['angle'])
                
                return True
            else:
                self.stats['frames_failed'] += 1
                return False
                
        except requests.exceptions.Timeout:
            self.stats['frames_failed'] += 1
            return False
        except Exception as e:
            self.stats['frames_failed'] += 1
            print_error(f"Error enviando frame: {str(e)}")
            return False
    
    def receive_processed_stream(self):
        """Recibe el stream procesado desde Railway (con visualización)"""
        print_info("Conectando al stream procesado...")
        
        try:
            stream_url = f"{self.railway_url}/api/stream/shoulder/{self.exercise_type}"
            
            response = self.session.get(stream_url, stream=True, timeout=10)
            
            if response.status_code != 200:
                print_error(f"Error en stream: {response.status_code}")
                return None
            
            # Procesar stream multipart
            buffer = b''
            for chunk in response.iter_content(chunk_size=1024):
                if not self.running:
                    break
                
                buffer += chunk
                
                # Buscar boundary entre frames
                a = buffer.find(b'\xff\xd8')  # JPEG start
                b = buffer.find(b'\xff\xd9')  # JPEG end
                
                if a != -1 and b != -1:
                    jpg = buffer[a:b+2]
                    buffer = buffer[b+2:]
                    
                    # Decodificar JPEG
                    frame = cv2.imdecode(
                        np.frombuffer(jpg, dtype=np.uint8),
                        cv2.IMREAD_COLOR
                    )
                    
                    if frame is not None:
                        self.stats['frames_received'] += 1
                        
                        # Agregar a queue (no bloqueante)
                        try:
                            self.processed_frame_queue.put_nowait(frame)
                        except queue.Full:
                            # Si la queue está llena, sacar el frame viejo
                            try:
                                self.processed_frame_queue.get_nowait()
                                self.processed_frame_queue.put_nowait(frame)
                            except:
                                pass
            
        except Exception as e:
            print_error(f"Error recibiendo stream: {str(e)}")
    
    def start_streaming(self, camera_id=0, show_window=True):
        """
        Inicia el streaming bidireccional
        
        Args:
            camera_id: ID de la cámara (0 para default)
            show_window: Si mostrar ventana de visualización
        """
        print_header("INICIANDO STREAMING CON RAILWAY")
        
        # Abrir cámara
        cap = cv2.VideoCapture(camera_id)
        
        if not cap.isOpened():
            print_error("No se pudo abrir la cámara")
            return
        
        # Configurar resolución
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        print_success("Cámara abierta correctamente")
        
        # Iniciar estadísticas
        self.stats['start_time'] = time.time()
        self.running = True
        
        # Iniciar thread para recibir stream procesado
        self.receive_thread = Thread(target=self.receive_processed_stream, daemon=True)
        self.receive_thread.start()
        
        print_info("Presiona 'Q' para salir")
        print_info("Presiona 'S' para ver estadísticas")
        print()
        
        frame_count = 0
        last_stats_print = time.time()
        
        try:
            while self.running:
                ret, frame = cap.read()
                
                if not ret:
                    print_warning("No se pudo leer frame de la cámara")
                    continue
                
                frame_count += 1
                
                # Espejo
                frame = cv2.flip(frame, 1)
                
                # Enviar frame a Railway cada 2 frames (reduce carga)
                if frame_count % 2 == 0:
                    self.send_frame(frame)
                
                # Mostrar frame
                if show_window:
                    display_frame = frame.copy()
                    
                    # Intentar obtener frame procesado
                    try:
                        processed_frame = self.processed_frame_queue.get_nowait()
                        display_frame = processed_frame
                    except queue.Empty:
                        # Si no hay frame procesado, usar el original
                        pass
                    
                    # Agregar overlay con información
                    with self.lock:
                        if self.latest_angle is not None:
                            # Ángulo actual
                            cv2.putText(
                                display_frame,
                                f"Angulo: {self.latest_angle:.1f} deg",
                                (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                1,
                                (0, 255, 0),
                                2
                            )
                        
                        # Estadísticas en tiempo real
                        avg_latency = (self.stats['total_latency'] / self.stats['frames_sent']) if self.stats['frames_sent'] > 0 else 0
                        
                        cv2.putText(
                            display_frame,
                            f"Latencia: {avg_latency:.0f}ms",
                            (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (255, 255, 255),
                            1
                        )
                        
                        cv2.putText(
                            display_frame,
                            f"Enviados: {self.stats['frames_sent']} | Recibidos: {self.stats['frames_received']}",
                            (10, 85),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (200, 200, 200),
                            1
                        )
                    
                    cv2.imshow('Test Railway - Presiona Q para salir', display_frame)
                
                # Manejar teclas
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q') or key == ord('Q'):
                    print_info("Usuario solicitó salir")
                    break
                elif key == ord('s') or key == ord('S'):
                    self.print_stats()
                
                # Imprimir estadísticas cada 5 segundos
                if time.time() - last_stats_print > 5:
                    self.print_stats_inline()
                    last_stats_print = time.time()
        
        except KeyboardInterrupt:
            print_warning("Interrumpido por el usuario")
        
        finally:
            self.running = False
            cap.release()
            cv2.destroyAllWindows()
            
            # Esperar threads
            if self.receive_thread:
                self.receive_thread.join(timeout=2)
            
            # Reporte final
            self.print_final_report()
    
    def print_stats_inline(self):
        """Imprime estadísticas en una línea"""
        with self.lock:
            avg_latency = (self.stats['total_latency'] / self.stats['frames_sent']) if self.stats['frames_sent'] > 0 else 0
            angle_text = f"{self.latest_angle:.1f}°" if self.latest_angle else "N/A"
            
            print(f"\r📊 Enviados: {self.stats['frames_sent']} | Recibidos: {self.stats['frames_received']} | "
                  f"Latencia: {avg_latency:.0f}ms | Ángulo: {angle_text}     ", end='', flush=True)
    
    def print_stats(self):
        """Imprime estadísticas detalladas"""
        print("\n")
        print_header("ESTADÍSTICAS EN TIEMPO REAL")
        
        with self.lock:
            elapsed = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
            fps_sent = self.stats['frames_sent'] / elapsed if elapsed > 0 else 0
            fps_received = self.stats['frames_received'] / elapsed if elapsed > 0 else 0
            avg_latency = (self.stats['total_latency'] / self.stats['frames_sent']) if self.stats['frames_sent'] > 0 else 0
            success_rate = (self.stats['frames_sent'] / (self.stats['frames_sent'] + self.stats['frames_failed']) * 100) if (self.stats['frames_sent'] + self.stats['frames_failed']) > 0 else 0
            
            print(f"⏱️  Duración: {elapsed:.1f}s")
            print(f"📤 Frames enviados: {self.stats['frames_sent']} ({fps_sent:.1f} FPS)")
            print(f"📥 Frames recibidos: {self.stats['frames_received']} ({fps_received:.1f} FPS)")
            print(f"❌ Frames fallidos: {self.stats['frames_failed']}")
            print(f"✅ Tasa de éxito: {success_rate:.1f}%")
            print(f"⚡ Latencia promedio: {avg_latency:.0f}ms")
            print(f"⚡ Latencia máxima: {self.stats['max_latency']:.0f}ms")
            print(f"⚡ Latencia mínima: {self.stats['min_latency']:.0f}ms")
            
            if self.stats['angles_received'] > 0:
                print(f"\n📐 Ángulos recibidos: {self.stats['angles_received']}")
                print(f"📐 Ángulo mínimo: {self.stats['min_angle']:.1f}°")
                print(f"📐 Ángulo máximo: {self.stats['max_angle']:.1f}°")
                print(f"📐 ROM alcanzado: {self.stats['max_angle'] - self.stats['min_angle']:.1f}°")
            
            if self.latest_angle:
                print(f"📐 Ángulo actual: {self.latest_angle:.1f}°")
        
        print()
    
    def print_final_report(self):
        """Imprime reporte final"""
        print("\n")
        print_header("REPORTE FINAL")
        
        with self.lock:
            elapsed = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
            fps_sent = self.stats['frames_sent'] / elapsed if elapsed > 0 else 0
            fps_received = self.stats['frames_received'] / elapsed if elapsed > 0 else 0
            avg_latency = (self.stats['total_latency'] / self.stats['frames_sent']) if self.stats['frames_sent'] > 0 else 0
            success_rate = (self.stats['frames_sent'] / (self.stats['frames_sent'] + self.stats['frames_failed']) * 100) if (self.stats['frames_sent'] + self.stats['frames_failed']) > 0 else 0
            
            print(f"\n📊 RESUMEN DE LA SESIÓN:")
            print(f"   • Duración total: {elapsed:.1f} segundos")
            print(f"   • Frames enviados: {self.stats['frames_sent']} ({fps_sent:.1f} FPS)")
            print(f"   • Frames recibidos: {self.stats['frames_received']} ({fps_received:.1f} FPS)")
            print(f"   • Tasa de éxito: {success_rate:.1f}%")
            
            print(f"\n⚡ LATENCIA:")
            print(f"   • Promedio: {avg_latency:.0f}ms")
            print(f"   • Máxima: {self.stats['max_latency']:.0f}ms")
            print(f"   • Mínima: {self.stats['min_latency']:.0f}ms")
            
            if self.stats['angles_received'] > 0:
                print(f"\n📐 MEDICIONES:")
                print(f"   • Ángulos recibidos: {self.stats['angles_received']}")
                print(f"   • Rango medido: {self.stats['min_angle']:.1f}° - {self.stats['max_angle']:.1f}°")
                print(f"   • ROM total: {self.stats['max_angle'] - self.stats['min_angle']:.1f}°")
            
            print(f"\n✅ EVALUACIÓN:")
            
            if avg_latency < 100:
                print_success(f"Latencia excelente: {avg_latency:.0f}ms (objetivo: <100ms)")
            elif avg_latency < 200:
                print_info(f"Latencia aceptable: {avg_latency:.0f}ms (objetivo: <100ms)")
            else:
                print_warning(f"Latencia alta: {avg_latency:.0f}ms (objetivo: <100ms)")
            
            if success_rate >= 95:
                print_success(f"Tasa de éxito excelente: {success_rate:.1f}% (objetivo: >95%)")
            elif success_rate >= 80:
                print_info(f"Tasa de éxito aceptable: {success_rate:.1f}% (objetivo: >95%)")
            else:
                print_warning(f"Tasa de éxito baja: {success_rate:.1f}% (objetivo: >95%)")
            
            if fps_sent >= 15:
                print_success(f"FPS de envío excelente: {fps_sent:.1f} (objetivo: >15)")
            else:
                print_warning(f"FPS de envío bajo: {fps_sent:.1f} (objetivo: >15)")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='🚂 Test de streaming con Railway',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Con variable de entorno
  export RAILWAY_URL="https://tu-app.railway.app"
  python test_shoulder_railway.py --exercise flexion
  
  # Con URL directa
  python test_shoulder_railway.py --url https://tu-app.railway.app --exercise flexion
  
  # Especificar cámara
  python test_shoulder_railway.py --url https://tu-app.railway.app --camera 1
        """
    )
    
    parser.add_argument('--url',
                       type=str,
                       default=os.environ.get('RAILWAY_URL'),
                       help='URL de tu app en Railway (o usa RAILWAY_URL env var)')
    
    parser.add_argument('--exercise',
                       choices=['flexion', 'extension', 'abduction', 'external_rotation'],
                       default='flexion',
                       help='Tipo de ejercicio a probar (default: flexion)')
    
    parser.add_argument('--camera',
                       type=int,
                       default=0,
                       help='ID de la cámara (default: 0)')
    
    parser.add_argument('--no-window',
                       action='store_true',
                       help='No mostrar ventana de visualización')
    
    args = parser.parse_args()
    
    # Banner
    print("\n" + "="*70)
    print(f"{Colors.BOLD}{Colors.HEADER}🚂 TEST DE STREAMING CON RAILWAY{Colors.ENDC}")
    print("="*70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    # Verificar URL
    if not args.url:
        print_error("No se especificó URL de Railway")
        print_info("Usa: --url https://tu-app.railway.app")
        print_info("O configura: export RAILWAY_URL='https://tu-app.railway.app'")
        return
    
    # Crear cliente
    client = RailwayStreamingClient(args.url, args.exercise)
    
    # Test de conexión
    if not client.test_connection():
        print_error("No se pudo conectar a Railway. Abortando.")
        return
    
    # Configurar ejercicio
    if not client.set_exercise():
        print_warning("No se pudo configurar ejercicio, continuando de todos modos...")
    
    # Iniciar streaming
    print_info(f"\n📋 INSTRUCCIONES para {args.exercise.upper()}:")
    
    if args.exercise == 'flexion':
        print_info("   - Posición: De PERFIL a la cámara")
        print_info("   - Movimiento: Levanta el brazo hacia ADELANTE")
    elif args.exercise == 'abduction':
        print_info("   - Posición: De FRENTE a la cámara")
        print_info("   - Movimiento: Levanta el brazo hacia el LADO")
    elif args.exercise == 'extension':
        print_info("   - Posición: De PERFIL a la cámara")
        print_info("   - Movimiento: Lleva el brazo hacia ATRÁS")
    elif args.exercise == 'external_rotation':
        print_info("   - Posición: De FRENTE a la cámara")
        print_info("   - Movimiento: Rota el hombro hacia afuera")
    
    print()
    
    # Iniciar
    client.start_streaming(
        camera_id=args.camera,
        show_window=not args.no_window
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}⚠️  Ejecución interrumpida por el usuario{Colors.ENDC}\n")
    except Exception as e:
        print(f"\n\n{Colors.FAIL}❌ ERROR FATAL: {str(e)}{Colors.ENDC}\n")
        import traceback
        traceback.print_exc()
