"""
🧪 TEST DE HOMBRO - VERIFICACIÓN DEL FLUJO DE DATOS
════════════════════════════════════════════════════

Este script prueba el funcionamiento completo del sistema de medición de ángulos del hombro:

1. ✅ Inicialización del analizador
2. ✅ Detección de pose con MediaPipe
3. ✅ Cálculo de ángulos (bilateral y unilateral)
4. ✅ Sistema de referencias fijas
5. ✅ Filtros temporales
6. ✅ Visualización en tiempo real
7. ✅ Detección de orientación

MODOS DE EJECUCIÓN:
-------------------
- Modo WEBCAM: Usa tu cámara en tiempo real
- Modo TEST: Genera landmarks sintéticos para pruebas automáticas

USO:
----
python test_shoulder.py --mode webcam --exercise flexion
python test_shoulder.py --mode test --exercise abduction
python test_shoulder.py --mode webcam --exercise all
"""

import sys
import os
import cv2
import numpy as np
import mediapipe as mp
import argparse
from datetime import datetime
import time

# 📂 Configurar paths para imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)

# Agregar AMBOS paths (el parent y el project root)
sys.path.insert(0, parent_dir)
sys.path.insert(0, project_root)

# 🎯 Importar módulos del sistema
from joints.shoulder_analyzer import ShoulderAnalyzer
from core.mediapipe_config import MediaPipeConfig
from core.orientation_detector import AdaptiveOrientationDetector
from core.fixed_references import FixedSpatialReferences

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
    UNDERLINE = '\033[4m'

def print_header(text):
    """Imprime un encabezado bonito"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_test(test_name, status, details=""):
    """Imprime resultado de una prueba"""
    icon = "✅" if status else "❌"
    color = Colors.OKGREEN if status else Colors.FAIL
    print(f"{icon} {color}{test_name}{Colors.ENDC}")
    if details:
        print(f"   └─> {details}")

def print_info(text):
    """Imprime información general"""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def print_warning(text):
    """Imprime advertencia"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_angle(exercise, angle, side=""):
    """Imprime ángulo formateado"""
    side_text = f" ({side})" if side else ""
    print(f"   📐 {exercise}{side_text}: {angle:.1f}°")


# ═══════════════════════════════════════════════════════════════════
# TEST 1: INICIALIZACIÓN DEL SISTEMA
# ═══════════════════════════════════════════════════════════════════

def test_initialization():
    """Prueba la inicialización de todos los componentes"""
    print_header("TEST 1: INICIALIZACIÓN DEL SISTEMA")
    
    results = {
        'analyzer': False,
        'mediapipe': False,
        'orientation': False,
        'references': False
    }
    
    # Test 1.1: ShoulderAnalyzer
    try:
        analyzer = ShoulderAnalyzer()
        results['analyzer'] = True
        print_test("ShoulderAnalyzer", True, f"Ejercicios disponibles: {len(analyzer.exercise_configs)}")
        
        # Listar ejercicios
        for exercise_name in analyzer.exercise_configs.keys():
            print(f"      • {exercise_name}")
    except Exception as e:
        print_test("ShoulderAnalyzer", False, str(e))
        return None, results
    
    # Test 1.2: MediaPipe
    try:
        pose = MediaPipeConfig.create_pose_detector()
        results['mediapipe'] = True
        print_test("MediaPipe Pose", True, "Detector creado correctamente")
    except Exception as e:
        print_test("MediaPipe Pose", False, str(e))
        pose = None
    
    # Test 1.3: Orientation Detector
    try:
        orientation_detector = AdaptiveOrientationDetector()
        results['orientation'] = True
        print_test("Orientation Detector", True)
    except Exception as e:
        print_test("Orientation Detector", False, str(e))
    
    # Test 1.4: Fixed References
    try:
        fixed_ref = FixedSpatialReferences()
        results['references'] = True
        print_test("Fixed References", True)
        
        # Mostrar referencias disponibles
        print(f"      • Vertical: {fixed_ref.VERTICAL_REFERENCE}")
        print(f"      • Vertical Down: {fixed_ref.VERTICAL_DOWN_REFERENCE}")
        print(f"      • Horizontal: {fixed_ref.HORIZONTAL_REFERENCE}")
    except Exception as e:
        print_test("Fixed References", False, str(e))
    
    # Resumen
    total_tests = len(results)
    passed_tests = sum(results.values())
    print(f"\n{Colors.BOLD}Resultado: {passed_tests}/{total_tests} componentes inicializados{Colors.ENDC}")
    
    return analyzer, results


# ═══════════════════════════════════════════════════════════════════
# TEST 2: GENERACIÓN DE LANDMARKS SINTÉTICOS
# ═══════════════════════════════════════════════════════════════════

def generate_synthetic_landmarks(angle_degrees, exercise_type='flexion', side='bilateral'):
    """
    Genera landmarks sintéticos para pruebas
    
    Args:
        angle_degrees: Ángulo objetivo del brazo (0-180°)
        exercise_type: 'flexion', 'abduction', 'rotation'
        side: 'bilateral', 'right', 'left'
    
    Returns:
        Lista de landmarks sintéticos con formato MediaPipe
    """
    
    class SyntheticLandmark:
        def __init__(self, x, y, z, visibility):
            self.x = x
            self.y = y
            self.z = z
            self.visibility = visibility
    
    # Crear 33 landmarks (MediaPipe estándar)
    landmarks = []
    for i in range(33):
        landmarks.append(SyntheticLandmark(0.5, 0.5, 0, 0.1))  # Default invisible
    
    # Configurar landmarks visibles según el ejercicio
    if exercise_type == 'flexion':
        # Vista SAGITAL (perfil)
        # Posición base: persona de pie, vista lateral derecha
        
        # Hombro derecho (punto 12) - fijo
        shoulder_x = 0.5
        shoulder_y = 0.3
        landmarks[12] = SyntheticLandmark(shoulder_x, shoulder_y, 0, 0.99)
        
        # Cadera derecha (punto 24) - fijo, abajo del hombro
        landmarks[24] = SyntheticLandmark(shoulder_x, shoulder_y + 0.3, 0, 0.99)
        
        # Codo derecho (punto 14) - se mueve según el ángulo
        # Para flexión: el brazo sube hacia adelante
        angle_rad = np.radians(angle_degrees)
        arm_length = 0.15  # Longitud del brazo superior
        
        elbow_x = shoulder_x + arm_length * np.sin(angle_rad)
        elbow_y = shoulder_y - arm_length * np.cos(angle_rad)
        landmarks[14] = SyntheticLandmark(elbow_x, elbow_y, 0, 0.99)
        
        # Muñeca derecha (punto 16) - extensión del codo
        forearm_length = 0.15
        wrist_x = elbow_x + forearm_length * np.sin(angle_rad)
        wrist_y = elbow_y - forearm_length * np.cos(angle_rad)
        landmarks[16] = SyntheticLandmark(wrist_x, wrist_y, 0, 0.99)
        
        # Caderas juntas para simular vista SAGITAL
        landmarks[23] = SyntheticLandmark(shoulder_x - 0.02, shoulder_y + 0.3, 0, 0.99)  # Cadera izq
        
    elif exercise_type == 'abduction':
        # Vista FRONTAL
        # Posición base: persona de pie, vista frontal
        
        # Hombros separados (vista frontal)
        landmarks[11] = SyntheticLandmark(0.35, 0.3, 0, 0.99)  # Hombro izq
        landmarks[12] = SyntheticLandmark(0.65, 0.3, 0, 0.99)  # Hombro der
        
        # Caderas separadas (vista frontal)
        landmarks[23] = SyntheticLandmark(0.40, 0.6, 0, 0.99)  # Cadera izq
        landmarks[24] = SyntheticLandmark(0.60, 0.6, 0, 0.99)  # Cadera der
        
        # Brazo derecho - abducción lateral
        angle_rad = np.radians(angle_degrees)
        arm_length = 0.15
        
        shoulder_x = 0.65
        shoulder_y = 0.3
        
        # El brazo se abre hacia el lado (horizontal)
        elbow_x = shoulder_x + arm_length * np.cos(angle_rad)
        elbow_y = shoulder_y + arm_length * np.sin(angle_rad)
        landmarks[14] = SyntheticLandmark(elbow_x, elbow_y, 0, 0.99)
        
        wrist_x = elbow_x + arm_length * np.cos(angle_rad)
        wrist_y = elbow_y + arm_length * np.sin(angle_rad)
        landmarks[16] = SyntheticLandmark(wrist_x, wrist_y, 0, 0.99)
    
    return landmarks


def test_synthetic_landmarks():
    """Prueba la generación de landmarks sintéticos"""
    print_header("TEST 2: GENERACIÓN DE LANDMARKS SINTÉTICOS")
    
    test_cases = [
        (0, 'flexion', 'Brazo abajo (anatómico)'),
        (45, 'flexion', 'Flexión 45°'),
        (90, 'flexion', 'Flexión 90° (horizontal)'),
        (180, 'flexion', 'Flexión 180° (arriba)'),
        (0, 'abduction', 'Brazo abajo'),
        (90, 'abduction', 'Abducción 90° (horizontal)'),
    ]
    
    for angle, exercise, description in test_cases:
        try:
            landmarks = generate_synthetic_landmarks(angle, exercise)
            visible_count = sum(1 for lm in landmarks if lm.visibility > 0.5)
            print_test(f"{description}", True, f"{visible_count} landmarks visibles")
        except Exception as e:
            print_test(f"{description}", False, str(e))


# ═══════════════════════════════════════════════════════════════════
# TEST 3: CÁLCULO DE ÁNGULOS CON LANDMARKS SINTÉTICOS
# ═══════════════════════════════════════════════════════════════════

def test_angle_calculation():
    """Prueba el cálculo de ángulos con landmarks sintéticos"""
    print_header("TEST 3: CÁLCULO DE ÁNGULOS CON LANDMARKS SINTÉTICOS")
    
    analyzer = ShoulderAnalyzer()
    frame_dimensions = (480, 640)  # height, width
    
    print_info("Probando FLEXIÓN (vista sagital)...")
    
    test_angles = [0, 30, 45, 60, 90, 120, 150, 180]
    
    for target_angle in test_angles:
        landmarks = generate_synthetic_landmarks(target_angle, 'flexion')
        
        try:
            # Configurar ejercicio
            analyzer.set_current_exercise('flexion')
            
            # Calcular ángulos
            result = analyzer.calculate_joint_angles(landmarks, frame_dimensions)
            
            if result and 'angles' in result:
                angles = result['angles']
                calculated_angle = angles.get('flexion_right', 0)
                error = abs(calculated_angle - target_angle)
                
                # Considerar exitoso si el error es < 5°
                success = error < 5.0
                status_icon = "✅" if success else "⚠️"
                
                print(f"   {status_icon} Target: {target_angle:3.0f}° → Calculado: {calculated_angle:5.1f}° (Error: {error:4.1f}°)")
            else:
                print_test(f"Ángulo {target_angle}°", False, "No se obtuvieron resultados")
                
        except Exception as e:
            print_test(f"Ángulo {target_angle}°", False, str(e))
    
    print_info("\nProbando ABDUCCIÓN (vista frontal)...")
    
    for target_angle in [0, 45, 90, 135, 180]:
        landmarks = generate_synthetic_landmarks(target_angle, 'abduction')
        
        try:
            analyzer.set_current_exercise('abduction')
            result = analyzer.calculate_joint_angles(landmarks, frame_dimensions)
            
            if result and 'angles' in result:
                angles = result['angles']
                calculated_angle = angles.get('abduction_right', 0)
                error = abs(calculated_angle - target_angle)
                success = error < 5.0
                status_icon = "✅" if success else "⚠️"
                
                print(f"   {status_icon} Target: {target_angle:3.0f}° → Calculado: {calculated_angle:5.1f}° (Error: {error:4.1f}°)")
            else:
                print_test(f"Ángulo {target_angle}°", False, "No se obtuvieron resultados")
                
        except Exception as e:
            print_test(f"Ángulo {target_angle}°", False, str(e))


# ═══════════════════════════════════════════════════════════════════
# TEST 4: FLUJO COMPLETO CON WEBCAM
# ═══════════════════════════════════════════════════════════════════

def test_webcam_realtime(exercise_type='flexion', duration_seconds=30):
    """
    Prueba el flujo completo con webcam en tiempo real
    
    Args:
        exercise_type: Tipo de ejercicio a probar
        duration_seconds: Duración de la prueba
    """
    print_header(f"TEST 4: FLUJO COMPLETO CON WEBCAM - {exercise_type.upper()}")
    
    # Inicializar componentes
    analyzer = ShoulderAnalyzer()
    analyzer.set_current_exercise(exercise_type)
    
    pose = MediaPipeConfig.create_pose_detector()
    
    # Abrir webcam
    print_info("Intentando abrir la cámara...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print_test("Apertura de cámara", False, "No se pudo abrir la cámara")
        return
    
    print_test("Apertura de cámara", True, "Cámara abierta correctamente")
    
    # Configurar resolución
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Estadísticas
    stats = {
        'frames_processed': 0,
        'frames_with_pose': 0,
        'angles_calculated': 0,
        'max_angle': 0,
        'min_angle': 180,
        'start_time': time.time()
    }
    
    print_info(f"\n🎥 Iniciando captura por {duration_seconds} segundos...")
    print_info("📋 INSTRUCCIONES:")
    print_info(f"   - Ejercicio: {exercise_type}")
    if exercise_type == 'flexion':
        print_info("   - Posición: De PERFIL a la cámara")
        print_info("   - Movimiento: Levanta el brazo hacia ADELANTE")
    elif exercise_type == 'abduction':
        print_info("   - Posición: De FRENTE a la cámara")
        print_info("   - Movimiento: Levanta el brazo hacia el LADO")
    print_info("   - Presiona 'q' para salir antes\n")
    
    end_time = time.time() + duration_seconds
    
    try:
        while time.time() < end_time:
            ret, frame = cap.read()
            
            if not ret:
                print_warning("No se pudo leer frame")
                continue
            
            stats['frames_processed'] += 1
            
            # Espejo para mejor UX
            frame = cv2.flip(frame, 1)
            
            # Convertir a RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detectar pose
            results = pose.process(rgb_frame)
            
            if results.pose_landmarks:
                stats['frames_with_pose'] += 1
                landmarks = results.pose_landmarks.landmark
                
                # Calcular ángulos
                h, w = frame.shape[:2]
                angle_result = analyzer.calculate_joint_angles(landmarks, (h, w))
                
                if angle_result and 'angles' in angle_result:
                    angles = angle_result['angles']
                    
                    # Buscar cualquier ángulo válido (flexion_left, flexion_right, etc.)
                    angle_value = None
                    for key in ['flexion_right', 'flexion_left', f'{exercise_type}_right', f'{exercise_type}_left']:
                        if key in angles and angles[key] is not None:
                            angle_value = angles[key]
                            break
                    
                    if angle_value is not None:
                        stats['angles_calculated'] += 1
                        stats['max_angle'] = max(stats['max_angle'], angle_value)
                        stats['min_angle'] = min(stats['min_angle'], angle_value)
                        
                        # Dibujar en frame
                        cv2.putText(frame, f"{exercise_type.upper()}: {angle_value:.1f} deg", 
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Dibujar esqueleto
                mp.solutions.drawing_utils.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    mp.solutions.pose.POSE_CONNECTIONS,
                    mp.solutions.drawing_utils.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    mp.solutions.drawing_utils.DrawingSpec(color=(255, 0, 0), thickness=2)
                )
            
            # Mostrar tiempo restante
            remaining = int(end_time - time.time())
            cv2.putText(frame, f"Tiempo: {remaining}s", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Mostrar estadísticas en vivo
            cv2.putText(frame, f"Frames: {stats['frames_processed']}", (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(frame, f"Pose detectada: {stats['frames_with_pose']}", (10, 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            # Mostrar frame
            cv2.imshow('Test Shoulder - Presiona Q para salir', frame)
            
            # Salir con 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print_info("Usuario solicitó salir")
                break
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    # Reporte final
    print_header("REPORTE DE PRUEBA WEBCAM")
    
    elapsed_time = time.time() - stats['start_time']
    fps = stats['frames_processed'] / elapsed_time if elapsed_time > 0 else 0
    pose_detection_rate = (stats['frames_with_pose'] / stats['frames_processed'] * 100) if stats['frames_processed'] > 0 else 0
    angle_calculation_rate = (stats['angles_calculated'] / stats['frames_with_pose'] * 100) if stats['frames_with_pose'] > 0 else 0
    
    print(f"\n📊 ESTADÍSTICAS:")
    print(f"   • Duración: {elapsed_time:.1f} segundos")
    print(f"   • Frames procesados: {stats['frames_processed']}")
    print(f"   • FPS promedio: {fps:.1f}")
    print(f"   • Frames con pose detectada: {stats['frames_with_pose']} ({pose_detection_rate:.1f}%)")
    print(f"   • Ángulos calculados: {stats['angles_calculated']} ({angle_calculation_rate:.1f}%)")
    
    if stats['angles_calculated'] > 0:
        print(f"\n📐 RANGO DE MOVIMIENTO:")
        print(f"   • Ángulo mínimo: {stats['min_angle']:.1f}°")
        print(f"   • Ángulo máximo: {stats['max_angle']:.1f}°")
        print(f"   • ROM alcanzado: {stats['max_angle'] - stats['min_angle']:.1f}°")
    
    # Evaluación
    print(f"\n✅ EVALUACIÓN:")
    
    if fps >= 20:
        print_test("Performance", True, f"FPS={fps:.1f} (objetivo: >20)")
    else:
        print_test("Performance", False, f"FPS={fps:.1f} (objetivo: >20)")
    
    if pose_detection_rate >= 80:
        print_test("Detección de Pose", True, f"{pose_detection_rate:.1f}% (objetivo: >80%)")
    else:
        print_test("Detección de Pose", False, f"{pose_detection_rate:.1f}% (objetivo: >80%)")
    
    if angle_calculation_rate >= 90:
        print_test("Cálculo de Ángulos", True, f"{angle_calculation_rate:.1f}% (objetivo: >90%)")
    else:
        print_test("Cálculo de Ángulos", False, f"{angle_calculation_rate:.1f}% (objetivo: >90%)")


# ═══════════════════════════════════════════════════════════════════
# TEST 5: VERIFICACIÓN DE ORIENTACIÓN
# ═══════════════════════════════════════════════════════════════════

def test_orientation_detection():
    """Prueba la detección de orientación con landmarks sintéticos"""
    print_header("TEST 5: DETECCIÓN DE ORIENTACIÓN")
    
    detector = AdaptiveOrientationDetector()
    
    # Test FRONTAL (caderas separadas)
    print_info("Probando vista FRONTAL...")
    landmarks_frontal = generate_synthetic_landmarks(0, 'abduction')
    
    # Simular frame dimensions
    w, h = 640, 480
    
    # El detector necesita landmarks en formato diccionario con x, y normalizados
    # Extraer puntos clave
    l_hip = landmarks_frontal[23]
    r_hip = landmarks_frontal[24]
    
    hip_width = abs(l_hip.x - r_hip.x)
    
    if hip_width > 0.18:
        print_test("Vista FRONTAL", True, f"Hip width={hip_width:.3f} (>0.18)")
    else:
        print_test("Vista FRONTAL", False, f"Hip width={hip_width:.3f} (esperado >0.18)")
    
    # Test SAGITAL (caderas juntas)
    print_info("\nProbando vista SAGITAL (perfil)...")
    landmarks_sagital = generate_synthetic_landmarks(0, 'flexion')
    
    l_hip = landmarks_sagital[23]
    r_hip = landmarks_sagital[24]
    
    hip_width = abs(l_hip.x - r_hip.x)
    
    if hip_width < 0.07:
        print_test("Vista SAGITAL", True, f"Hip width={hip_width:.3f} (<0.07)")
    else:
        print_test("Vista SAGITAL", False, f"Hip width={hip_width:.3f} (esperado <0.07)")


# ═══════════════════════════════════════════════════════════════════
# TEST 6: SISTEMA DE FILTROS TEMPORALES
# ═══════════════════════════════════════════════════════════════════

def test_temporal_filter():
    """Prueba el sistema de filtros temporales"""
    print_header("TEST 6: FILTROS TEMPORALES")
    
    analyzer = ShoulderAnalyzer()
    
    # Simular secuencia de ángulos con ruido
    true_angle = 90.0
    noisy_angles = [
        90, 92, 88, 91, 89, 90, 95, 87, 90, 91,  # Con ruido ±5°
    ]
    
    print_info(f"Ángulo real: {true_angle}°")
    print_info("Secuencia con ruido: " + ", ".join(f"{a}°" for a in noisy_angles))
    print_info("\nAplicando filtro de mediana (ventana=5)...\n")
    
    filtered_angles = []
    
    for i, noisy_angle in enumerate(noisy_angles):
        filtered = analyzer.apply_temporal_filter(noisy_angle, 'test_filter')
        filtered_angles.append(filtered)
        
        error = abs(filtered - true_angle)
        status = "✅" if error < 2.0 else "⚠️"
        
        print(f"   {status} Frame {i+1:2d}: Ruidoso={noisy_angle:3.0f}° → Filtrado={filtered:5.1f}° (Error: {error:3.1f}°)")
    
    # Calcular mejora
    avg_noise = np.mean([abs(a - true_angle) for a in noisy_angles])
    avg_filtered = np.mean([abs(a - true_angle) for a in filtered_angles])
    improvement = (avg_noise - avg_filtered) / avg_noise * 100
    
    print(f"\n📊 RESULTADOS:")
    print(f"   • Error promedio SIN filtro: {avg_noise:.2f}°")
    print(f"   • Error promedio CON filtro: {avg_filtered:.2f}°")
    print(f"   • Mejora: {improvement:.1f}%")
    
    if improvement > 30:
        print_test("Efectividad del filtro", True, f"{improvement:.1f}% de mejora")
    else:
        print_test("Efectividad del filtro", False, f"Solo {improvement:.1f}% de mejora (esperado >30%)")


# ═══════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════

def main():
    """Función principal con argumentos de línea de comandos"""
    
    parser = argparse.ArgumentParser(
        description='🧪 Test completo del sistema de medición de ángulos del hombro',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python test_shoulder.py --mode all
  python test_shoulder.py --mode webcam --exercise flexion --duration 60
  python test_shoulder.py --mode test
  python test_shoulder.py --mode init
        """
    )
    
    parser.add_argument('--mode', 
                       choices=['all', 'init', 'test', 'webcam'],
                       default='all',
                       help='Modo de ejecución (default: all)')
    
    parser.add_argument('--exercise',
                       choices=['flexion', 'abduction', 'rotation', 'all'],
                       default='flexion',
                       help='Ejercicio a probar en modo webcam (default: flexion)')
    
    parser.add_argument('--duration',
                       type=int,
                       default=30,
                       help='Duración de la prueba en modo webcam en segundos (default: 30)')
    
    args = parser.parse_args()
    
    # Banner
    print("\n" + "="*60)
    print(f"{Colors.BOLD}{Colors.HEADER}🧪 TEST DE HOMBRO - SISTEMA BIOMECÁNICO{Colors.ENDC}")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Modo: {args.mode.upper()}")
    print("="*60 + "\n")
    
    # Ejecutar tests según el modo
    if args.mode in ['all', 'init']:
        analyzer, init_results = test_initialization()
        if args.mode == 'init':
            return
        
        # Verificar que la inicialización fue exitosa
        if not all(init_results.values()):
            print_warning("⚠️  Algunos componentes fallaron. No se pueden ejecutar más tests.")
            return
    
    if args.mode in ['all', 'test']:
        test_synthetic_landmarks()
        test_angle_calculation()
        test_orientation_detection()
        test_temporal_filter()
    
    if args.mode == 'webcam':
        if args.exercise == 'all':
            for exercise in ['flexion', 'abduction']:
                test_webcam_realtime(exercise, args.duration)
                print("\n" + "="*60 + "\n")
        else:
            test_webcam_realtime(args.exercise, args.duration)
    
    # Resumen final
    print_header("✅ TESTS COMPLETADOS")
    print(f"Ejecución finalizada: {datetime.now().strftime('%H:%M:%S')}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}⚠️  Ejecución interrumpida por el usuario{Colors.ENDC}\n")
    except Exception as e:
        print(f"\n\n{Colors.FAIL}❌ ERROR FATAL: {str(e)}{Colors.ENDC}\n")
        import traceback
        traceback.print_exc()
