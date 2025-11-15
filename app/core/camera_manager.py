import cv2
import time
import json
from typing import Dict, List, Optional, Tuple

class SmartCameraManager:
    """
    🧠 GESTOR INTELIGENTE DE CÁMARAS
    🔍 Detecta automáticamente la mejor cámara disponible
    📱 Funciona con Camo, DroidCam, OBS, webcams normales
    """
    
    def __init__(self):
        self.detected_cameras = {}
        self.camera_cache = {}
        
        # 🎯 ORDEN DE PREFERENCIA (mejor primero)
        self.camera_priorities = {
            "high_res_external": 1,    # iPhone, Android alta calidad
            "standard_external": 2,    # Webcams HD externas
            "virtual_camera": 3,       # OBS, virtual cameras
            "built_in": 4              # Webcam laptop (último recurso)
        }
        
        # 📊 PATRONES PARA IDENTIFICAR TIPOS DE CÁMARA
        self.camera_patterns = {
            "camo_studio": {
                "min_width": 1920,
                "min_height": 1080,
                "typical_fps": [30, 60],
                "hints": ["alta_resolucion", "externa"]
            },
            "droidcam": {
                "min_width": 1280,
                "min_height": 720,
                "typical_fps": [25, 30],
                "hints": ["hd_externa", "movil"]
            },
            "obs_virtual": {
                "min_width": 1920,
                "min_height": 1080,
                "typical_fps": [30],
                "hints": ["virtual", "streaming"]
            },
            "laptop_webcam": {
                "max_width": 1280,
                "max_height": 720,
                "typical_fps": [30],
                "hints": ["integrada", "basica"]
            }
        }
    
    def scan_all_cameras(self, max_cameras: int = 4, timeout_per_camera: float = 1.0) -> Dict:
        """
        🔍 ESCANEA TODAS las cámaras disponibles
        📊 Clasifica por calidad, tipo y rendimiento
        """
        print("🔍 Iniciando escaneo inteligente de cámaras...")
        print("=" * 60)
        
        detected = {}
        
        for camera_id in range(max_cameras):
            print(f"📷 Probando cámara {camera_id}...", end=" ", flush=True)
            
            camera_info = self._test_camera(camera_id, timeout_per_camera)
            
            if camera_info:
                detected[camera_id] = camera_info
                print(f"✅ {camera_info['display_name']}")
                print(f"   📐 {camera_info['resolution']} @ {camera_info['fps']}fps")
                print(f"   🏷️ {camera_info['probable_type']}")
                
                # Mostrar hints si los hay
                if camera_info['app_hints']:
                    print(f"   💡 {', '.join(camera_info['app_hints'])}")
                
            else:
                print("❌ No disponible")
        
        self.detected_cameras = detected
        
        print("=" * 60)
        print(f"✅ Escaneo completado: {len(detected)} cámaras detectadas")
        
        return detected
    
    def _test_camera(self, camera_id: int, timeout: float) -> Optional[Dict]:
        """🔬 Prueba una cámara específica y extrae información"""
        
        cap = None
        try:
            start_time = time.time()
            
            cap = cv2.VideoCapture(camera_id)
            
            if not cap.isOpened():
                return None
            
            # ⚡ Test rápido de lectura
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # 🎯 Intentar configurar alta resolución
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            cap.set(cv2.CAP_PROP_FPS, 30)
            
            if time.time() - start_time > timeout:
                return None
            
            # 📸 Leer frame de prueba
            ret, frame = cap.read()
            
            if not ret or frame is None:
                print(f"⚠️ Cámara {camera_id}: No pudo leer frame (ret={ret})")
                return None
            
            # 📸 FIX 1.1 RELAJADO: Validar contenido del frame
            # Verificar brillo (detectar frames negros de Camo inactivo)
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_brightness = gray_frame.mean()
            
            # 🔧 RELAJADO: Solo rechazar si frame 100% negro (cámara bloqueada por Windows)
            if mean_brightness == 0:  # Frame completamente negro
                print(f"⚠️ Cámara {camera_id} BLOQUEADA o EN USO (brillo={mean_brightness:.1f})")
                print(f"   💡 SOLUCIÓN:")
                print(f"      1. Windows > Configuración > Privacidad > Cámara → Permitir acceso")
                print(f"      2. Cierra otras apps (Zoom, Teams, Skype, Chrome DevTools)")
                print(f"      3. Reinicia el navegador")
                return None
            elif mean_brightness < 3:  # Casi negro pero no completamente
                print(f"⚠️ Cámara {camera_id} brillo MUY bajo ({mean_brightness:.1f}) - ACEPTADA")
                print(f"   💡 Puede estar en ambiente oscuro o tapada")
            elif mean_brightness < 15:
                print(f"ℹ️ Cámara {camera_id} brillo bajo ({mean_brightness:.1f}) - OK")
            else:
                print(f"✅ Cámara {camera_id} brillo normal ({mean_brightness:.1f})")
            
            # Verificar movimiento (detectar frames congelados) - MÁS PERMISIVO
            ret2, frame2 = cap.read()
            if ret2 and frame2 is not None:
                gray_frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
                frame_diff = cv2.absdiff(gray_frame, gray_frame2).mean()
                
                # Solo rechazar si frames IDÉNTICOS y muy oscuro
                if frame_diff == 0 and mean_brightness < 5:
                    print(f"⚠️ Cámara {camera_id} frames idénticos + muy oscuro (diff={frame_diff:.2f})")
                    return None
                elif frame_diff < 0.5:
                    print(f"ℹ️ Cámara {camera_id} estática (diff={frame_diff:.2f}) - OK (sin movimiento)")
            
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(cap.get(cv2.CAP_PROP_FPS))
            
            # 🔍 Información adicional
            backend_name = cap.getBackendName()
            
            # 🏷️ Clasificar cámara
            camera_classification = self._classify_camera(
                camera_id, actual_width, actual_height, actual_fps, backend_name
            )
            
            return camera_classification
        
        except Exception as e:
            # 🔇 MEJORAR: Silenciar solo errores conocidos
            if "obsensor_uvc_stream_channel" not in str(e):
                print(f"Error desconocido: {e}")
            return None
    
    def _classify_camera(self, camera_id: int, width: int, height: int, fps: int, backend: str) -> Dict:
        """🏷️ Clasifica una cámara según sus características"""
        
        # 📊 Calcular score de calidad
        resolution_score = width * height
        quality_score = resolution_score * (fps / 30.0)  # Normalizar por 30fps
        
        # 🔍 Detectar tipo de cámara
        camera_type, probable_app = self._detect_camera_type(width, height, fps, camera_id)
        
        # 💡 Generar hints sobre la cámara
        app_hints = self._generate_camera_hints(width, height, fps, camera_id, probable_app)
        
        # 🎯 Determinar prioridad
        priority = self.camera_priorities.get(camera_type, 99)
        
        return {
            "id": camera_id,
            "width": width,
            "height": height,
            "fps": fps,
            "resolution": f"{width}x{height}",
            "quality_score": quality_score,
            "camera_type": camera_type,
            "probable_app": probable_app,
            "probable_type": f"{probable_app} ({camera_type})",
            "display_name": f"Cámara {camera_id}: {probable_app}",
            "app_hints": app_hints,
            "priority": priority,
            "backend": backend,
            "recommended": self._is_recommended_camera(camera_type, width, height)
        }
    
    def _detect_camera_type(self, width: int, height: int, fps: int, camera_id: int) -> Tuple[str, str]:
        """🕵️ Detecta el tipo de cámara y app probable"""
        
        # 📱 CAMO STUDIO / iPhone
        if width >= 1920 and height >= 1080 and camera_id >= 2:
            return "high_res_external", "Camo Studio/iPhone"
        
        # 📱 DROIDCAM HD (requiere validación igual que Camo)
        elif width >= 1280 and height >= 720 and width < 1920:
            return "external_mobile_app", "DroidCam/Android"
        
        # 🎥 OBS VIRTUAL CAMERA
        elif width >= 1920 and height >= 1080 and camera_id == 1:
            return "virtual_camera", "OBS Virtual Camera"
        
        # 📷 WEBCAM EXTERNA
        elif width >= 1280 and camera_id >= 1:
            return "standard_external", "Webcam Externa"
        
        # 💻 WEBCAM LAPTOP (típicamente camera_id = 0)
        elif camera_id == 0:
            return "built_in", "Webcam Laptop"
        
        # ❓ DESCONOCIDA
        else:
            return "built_in", f"Cámara Desconocida"
    
    def _generate_camera_hints(self, width: int, height: int, fps: int, camera_id: int, probable_app: str) -> List[str]:
        """💡 Genera hints útiles sobre la cámara"""
        
        hints = []
        
        # 📐 Hints por resolución
        if width >= 1920:
            hints.append("Full HD - Excelente para análisis")
        elif width >= 1280:
            hints.append("HD - Buena calidad")
        else:
            hints.append("Resolución básica")
        
        # 🎯 Hints por FPS
        if fps >= 60:
            hints.append("Alto FPS - Movimientos fluidos")
        elif fps >= 30:
            hints.append("FPS estándar")
        
        # 📱 Hints específicos por app
        if "Camo" in probable_app:
            hints.append("Requiere Camo Studio configurado")
        elif "DroidCam" in probable_app:
            hints.append("Requiere DroidCam configurado")
        elif "OBS" in probable_app:
            hints.append("Cámara virtual - Verifica OBS")
        elif "Laptop" in probable_app:
            hints.append("Calidad limitada - Considera externa")
        
        # 🎯 Recomendaciones de posición
        if camera_id >= 2:
            hints.append("Cámara externa - Óptima para biomecánica")
        
        return hints
    
    def _is_recommended_camera(self, camera_type: str, width: int, height: int) -> bool:
        """✅ Determina si una cámara es recomendada para análisis biomecánico"""
        
        # 🎯 Criterios para recomendación
        min_recommended_width = 1280
        min_recommended_height = 720
        
        is_good_resolution = width >= min_recommended_width and height >= min_recommended_height
        is_external = camera_type in ["high_res_external", "standard_external"]
        
        return is_good_resolution and is_external
    
    def get_best_camera(self) -> Optional[Dict]:
        """
        🎯 SELECCIONA automáticamente la mejor cámara disponible
        📊 Basado en calidad, tipo y recomendaciones
        """
        
        if not self.detected_cameras:
            print("⚠️ No hay cámaras escaneadas. Ejecuta scan_all_cameras() primero.")
            return None
        
        # 🏆 Ordenar cámaras por criterios múltiples
        sorted_cameras = sorted(
            self.detected_cameras.values(),
            key=lambda cam: (
                cam["priority"],           # Tipo de cámara (1 = mejor)
                -cam["quality_score"],     # Mayor calidad
                -cam["width"],             # Mayor resolución
                cam["id"]                  # ID menor como desempate
            )
        )
        
        best_camera = sorted_cameras[0]
        
        print("\n🎯 MEJOR CÁMARA SELECCIONADA:")
        print("=" * 40)
        print(f"   📷 {best_camera['display_name']}")
        print(f"   📐 Resolución: {best_camera['resolution']}")
        print(f"   🎬 FPS: {best_camera['fps']}")
        print(f"   ⭐ Score: {best_camera['quality_score']:.0f}")
        print(f"   ✅ Recomendada: {'Sí' if best_camera['recommended'] else 'No'}")
        
        if best_camera['app_hints']:
            print(f"   💡 Hints: {', '.join(best_camera['app_hints'])}")
        
        print("=" * 40)
        
        return best_camera
    
    def get_camera_recommendations(self) -> List[str]:
        """💡 Genera recomendaciones para mejorar el setup de cámara"""
        
        if not self.detected_cameras:
            return ["🔍 Ejecuta scan_all_cameras() para obtener recomendaciones"]
        
        recommendations = []
        
        # 📊 Análisis del setup actual
        total_cameras = len(self.detected_cameras)
        recommended_cameras = len([cam for cam in self.detected_cameras.values() if cam["recommended"]])
        best_resolution = max([cam["width"] * cam["height"] for cam in self.detected_cameras.values()])
        
        # 🎯 Recomendaciones específicas
        if recommended_cameras == 0:
            recommendations.append("📱 No hay cámaras externas - Considera DroidCam/Camo Studio")
            recommendations.append("💡 Webcam laptop tiene calidad limitada para análisis preciso")
        
        elif recommended_cameras == 1:
            recommendations.append("✅ Una buena cámara detectada - Setup adecuado")
        
        else:
            recommendations.append("🎯 Múltiples cámaras de calidad - Excelente setup")
        
        # 📐 Recomendaciones por resolución
        if best_resolution < 1280 * 720:
            recommendations.append("⚠️ Resolución baja - Mejora la cámara para mejor análisis")
        elif best_resolution >= 1920 * 1080:
            recommendations.append("🏆 Excelente resolución - Óptimo para análisis biomecánico")
        
        # 📊 Recomendaciones por cantidad
        if total_cameras <= 1:
            recommendations.append("📷 Solo una cámara - Considera backup o múltiples ángulos")
        
        return recommendations
    
    def create_camera_report(self) -> str:
        """📋 Crea un reporte detallado del setup de cámaras"""
        
        if not self.detected_cameras:
            return "❌ No hay cámaras detectadas. Ejecuta scan_all_cameras() primero."
        
        report = []
        report.append("📋 REPORTE DE CÁMARAS DETECTADAS")
        report.append("=" * 50)
        
        for cam_id, cam_info in self.detected_cameras.items():
            report.append(f"\n📷 CÁMARA {cam_id}:")
            report.append(f"   🏷️  Tipo: {cam_info['probable_type']}")
            report.append(f"   📐 Resolución: {cam_info['resolution']}")
            report.append(f"   🎬 FPS: {cam_info['fps']}")
            report.append(f"   ⭐ Score: {cam_info['quality_score']:.0f}")
            report.append(f"   ✅ Recomendada: {'Sí' if cam_info['recommended'] else 'No'}")
            
            if cam_info['app_hints']:
                report.append(f"   💡 Hints: {', '.join(cam_info['app_hints'])}")
        
        # Agregar recomendaciones
        recommendations = self.get_camera_recommendations()
        report.append(f"\n💡 RECOMENDACIONES:")
        for rec in recommendations:
            report.append(f"   {rec}")
        
        report.append("=" * 50)
        
        return "\n".join(report)
    
    def verify_camera_works_realtime(self, camera_id: int, test_frames: int = 5) -> bool:
        """
        ✅ VERIFICA que la cámara funcione en tiempo real
        📸 Lee múltiples frames para confirmar que no está congelada/negra
        """
        cap = None
        try:
            cap = cv2.VideoCapture(camera_id)
            
            if not cap.isOpened():
                return False
            
            # Configurar cámara
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            working_frames = 0
            
            for i in range(test_frames):
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    # 🔍 VERIFICAR que no sea frame negro/vacío
                    if self._is_frame_valid(frame):
                        working_frames += 1
                
                # Pequeña pausa entre frames
                cv2.waitKey(100)
            
            # ✅ Considera funcional si al menos 70% de frames son válidos
            success_rate = working_frames / test_frames
            return success_rate >= 0.7
            
        except Exception as e:
            return False
        
        finally:
            if cap:
                cap.release()
    
    def _is_frame_valid(self, frame) -> bool:
        """🔍 Verifica que el frame no esté negro/vacío/congelado"""
        
        if frame is None or frame.size == 0:
            return False
        
        # Convertir a escala de grises para análisis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 📊 Calcular estadísticas del frame
        mean_brightness = cv2.mean(gray)[0]
        std_brightness = cv2.meanStdDev(gray)[1][0][0]
        
        # 🔍 CRITERIOS DE VALIDEZ:
        # 1. No completamente negro (mean > 10)
        # 2. Tiene variación (std > 5) - no es frame sólido
        # 3. No completamente blanco (mean < 245)
        
        is_not_black = mean_brightness > 10
        has_variation = std_brightness > 5
        is_not_white = mean_brightness < 245
        
        return is_not_black and has_variation and is_not_white

# 🚀 FUNCIÓN HELPER MEJORADA CON FALLBACK
def auto_setup_camera_with_fallback() -> int:
    """
    🎯 SETUP AUTOMÁTICO CON FALLBACK INTELIGENTE
    ✅ Prueba cámaras hasta encontrar una que funcione realmente
    """
    
    print("🚀 CONFIGURACIÓN AUTOMÁTICA DE CÁMARA CON FALLBACK")
    print("=" * 60)
    
    # Crear manager y escanear
    manager = SmartCameraManager()
    detected_cameras = manager.scan_all_cameras()
    
    if not detected_cameras:
        print("❌ No se detectaron cámaras disponibles")
        print("💡 Verifica conexiones y permisos de cámara")
        return 0  # Fallback a cámara 0
    
    # 🏆 Ordenar cámaras por calidad (mejor primero)
    sorted_cameras = sorted(
        detected_cameras.values(),
        key=lambda cam: (
            cam["priority"],           # Tipo de cámara (1 = mejor)
            -cam["quality_score"],     # Mayor calidad
            -cam["width"],             # Mayor resolución
            cam["id"]                  # ID menor como desempate
        )
    )
    
    print(f"\n🔄 PROBANDO CÁMARAS EN ORDEN DE CALIDAD:")
    print("=" * 40)
    
    for i, camera in enumerate(sorted_cameras):
        camera_id = camera["id"]
        
        print(f"\n📷 PROBANDO CÁMARA {camera_id}: {camera['display_name']}")
        print(f"   📐 {camera['resolution']} @ {camera['fps']}fps")
        print(f"   🔍 Verificando funcionamiento real...", end=" ", flush=True)
        
        # ✅ VERIFICACIÓN EN TIEMPO REAL
        if manager.verify_camera_works_realtime(camera_id):
            print("✅ ¡FUNCIONA!")
            
            print(f"\n🎯 CÁMARA SELECCIONADA:")
            print("=" * 30)
            print(f"   📷 {camera['display_name']}")
            print(f"   📐 Resolución: {camera['resolution']}")
            print(f"   🎬 FPS: {camera['fps']}")
            print(f"   ⭐ Score: {camera['quality_score']:.0f}")
            print(f"   🔄 Posición en ranking: {i+1}")
            
            if camera['app_hints']:
                print(f"   💡 Hints: {', '.join(camera['app_hints'])}")
            
            print("=" * 60)
            
            return camera_id
        
        else:
            print("❌ No funciona (negro/congelado)")
            print(f"   💡 Saltando a siguiente opción...")
    
    # 😞 Si ninguna cámara funciona
    print("\n❌ NINGUNA CÁMARA FUNCIONA CORRECTAMENTE")
    print("💡 Usando cámara 0 como último recurso")
    print("🔧 Verifica apps de cámara (Camo, DroidCam) estén activas")
    print("=" * 60)
    
    return 0

# 🎯 SESSION 2: Validar UNA SOLA cámara (sin escanear todas)
def validate_single_camera(camera_id: int):
    """
    🎯 SESSION 2: Valida una cámara específica sin escanear todas
    Usado cuando LocalStorage tiene una cámara guardada
    
    Args:
        camera_id: ID de la cámara a validar
        
    Returns:
        Dict con info de la cámara si es válida, None si no
    """
    try:
        manager = SmartCameraManager()
        camera_info = manager._test_camera(camera_id)
        
        if camera_info:
            print(f"✅ SESSION 2: Cámara {camera_id} validada - {camera_info.get('display_name')}")
            
            # 💾 Guardar en bypass global
            from biomechanical_web_interface.handlers.camera_bypass import set_preselected_camera_global
            set_preselected_camera_global(camera_id, camera_info)
            
            return camera_info
        else:
            print(f"❌ SESSION 2: Cámara {camera_id} NO disponible o sin transmisión")
            return None
            
    except Exception as e:
        print(f"❌ Error validando cámara {camera_id}: {e}")
        return None

# 🚀 FUNCIÓN DE PRE-CARGA AL INICIO DE LA APP
def preload_cameras_at_startup():
    """
    🚀 EJECUTAR AL INICIAR APP (antes de cualquier análisis)
    Detecta cámaras disponibles y selecciona mejor automáticamente
    
    Returns:
        Dict con cámaras detectadas, o None si no hay cámaras
    """
    print("=" * 70)
    print("🔍 PRE-CARGA: Detectando cámaras disponibles al inicio...")
    print("=" * 70)
    
    try:
        manager = SmartCameraManager()
        cameras = manager.scan_all_cameras()  # ⏰ Solo UNA VEZ al inicio
        
        if not cameras:
            print("⚠️ No se encontraron cámaras")
            return None
        
        # Obtener mejor cámara
        best = manager.get_best_camera()
        
        # 💾 GUARDAR AUTOMÁTICAMENTE en bypass global
        if best:
            from biomechanical_web_interface.handlers.camera_bypass import set_preselected_camera_global
            set_preselected_camera_global(best['id'], best)
            print(f"\n✅ PRE-SELECCIONADA AUTOMÁTICAMENTE: Camera {best['id']}")
            print(f"   📷 {best['display_name']}")
            print(f"   📐 {best['resolution']} @ {best['fps']}fps")
            print("=" * 70)
        
        return cameras
        
    except Exception as e:
        print(f"❌ Error en pre-carga de cámaras: {e}")
        import traceback
        traceback.print_exc()
        return None

# 🆕 FUNCIÓN HELPER ESPECÍFICA PARA BIOMECÁNICA - SIMPLIFICADA
def auto_setup_camera_for_biomechanics(preselected_camera_id=None):
    """
    🧠 CONFIGURACIÓN PARA ANÁLISIS BIOMECÁNICO
    ✅ SIMPLIFICADA: Solo usa preselección del bypass, NO escanea
    
    FLUJO:
    1. Si hay argumento directo → usar
    2. Si hay variable global (bypass) → usar  
    3. Fallback → cámara 0 (sin escaneo)
    """
    from biomechanical_web_interface.handlers.camera_bypass import get_preselected_camera
    
    # 1️⃣ PRIORIDAD 1: Argumento directo (poco común)
    if preselected_camera_id is not None:
        print(f"✅ Usando cámara del argumento: {preselected_camera_id}")
        return preselected_camera_id, {'source': 'ARGUMENT'}
    
    # 2️⃣ PRIORIDAD 2: Variable global del bypass (gear icon o pre-carga)
    camera_id, info = get_preselected_camera()
    if camera_id is not None:
        print(f"✅ Usando cámara del bypass global: {camera_id}")
        print(f"   📷 Fuente: {info.get('source', 'PRE-CARGA O MANUAL')}")
        return camera_id, info
    
    # 3️⃣ FALLBACK: Cámara 0 por defecto (sin escaneo)
    print("⚠️ FALLBACK: No hay cámara preseleccionada, usando cámara 0")
    print("💡 Recomendación: Usar gear icon para seleccionar cámara manualmente")
    return 0, {'source': 'DEFAULT_FALLBACK'}

def scan_cameras_intelligent():
    """🔍 ESCANEA cámaras usando SmartCameraManager"""
    try:
        manager = SmartCameraManager()
        detected_cameras = manager.scan_all_cameras()
        
        camera_list = []
        for cam_id, cam_info in detected_cameras.items():
            camera_list.append({
                'id': cam_id,
                'name': cam_info.get('display_name', f'Cámara {cam_id}'),
                'probable_type': cam_info.get('probable_type', 'Desconocida'),
                'resolution': cam_info.get('resolution', 'Unknown'),
                'quality_score': cam_info.get('quality_score', 0),
                'recommended': cam_info.get('recommended', False)
            })
        
        return camera_list
        
    except Exception as e:
        print(f"❌ Error escaneando cámaras: {e}")
        return []

def find_best_camera_from_list(cameras):
    """🎯 ENCUENTRA la mejor cámara de una lista"""
    if not cameras:
        return None
    
    # Filtrar cámaras virtuales si hay reales disponibles
    real_cameras = [cam for cam in cameras if 'virtual' not in cam['probable_type'].lower()]
    
    if real_cameras:
        # Preferir cámaras reales
        sorted_cameras = sorted(real_cameras, key=lambda x: x.get('quality_score', 0), reverse=True)
    else:
        # Solo virtuales disponibles
        sorted_cameras = sorted(cameras, key=lambda x: x.get('quality_score', 0), reverse=True)
    
    return sorted_cameras[0]