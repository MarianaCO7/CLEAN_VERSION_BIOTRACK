# 📋 Contexto del Proyecto - Sistema de Análisis Biomecánico BIOTRACK

**Fecha de creación**: Noviembre 11, 2025  
**Versión**: V10_CLEAN  
**Estado actual**: Optimización del módulo de análisis de hombro antes de expandir a otros segmentos corporales

---

## 🖥️ ESPECIFICACIONES DE HARDWARE

### Laptop HP Omen
- **Procesador**: Intel Core i7-14650HX (14ª Generación, 2.20 GHz)
- **RAM**: 32 GB (31.7 GB usables)
- **GPU**: NVIDIA GeForce RTX 4060 (NO utilizada en el proyecto actual)
- **Sistema Operativo**: Windows 11
- **Shell**: bash.exe

### Cámara Web Integrada
- **Modelo**: Shcngqio TWC29
- **Resolución nativa REAL**: 720p @ 30 FPS
- **Conexión**: USB 2.0
- **Sensor**: 1/2.9"
- **Enfoque**: Manual (NO tiene autofocus)
- **Limitaciones**: 
  - NO soporta 1080p nativo de forma fiable
  - La documentación del TWC29 señala 720p como resolución técnica real
  - Para uso técnico debe considerarse 720p@30fps como base realista

---

## 🎯 OBJETIVO Y ALCANCE DEL PROYECTO

### Propósito Principal
Sistema de análisis biomecánico para evaluación de **Rango de Movimiento (ROM)** en articulaciones principales del cuerpo humano mediante visión por computadora.

### Contexto de Uso
- **Tipo**: Educativo (no médico/clínico)
- **Modalidad**: Tiempo real (análisis en vivo)
- **Usuarios simultáneos**: 1 persona por análisis
- **Cámaras**: 1 cámara por sesión de análisis
- **Portabilidad**: Aplicación web con interfaz Flask

### Segmentos Corporales a Analizar (Total: 5)
1. ✅ **Hombro** (Implementado actualmente)
   - Flexión/Extensión (vista de perfil)
   - Abducción bilateral (vista frontal)
2. ⏳ **Codo** (Por implementar)
3. ⏳ **Cadera** (Por implementar)
4. ⏳ **Rodilla** (Por implementar)
5. ⚠️ **Tobillo** (Por implementar - Requiere atención especial)

### Ejercicios por Segmento
- **Cantidad**: 2-3 ejercicios por segmento
- **Total estimado**: 10-15 ejercicios en el sistema completo

---

## 📊 RENDIMIENTO ACTUAL Y MÉTRICAS

### Performance Observado (Módulo de Hombro)
- ✅ **Fluidez visual**: El video se siente fluido y suave
- ✅ **Latencia**: Casi insignificante (< 50ms estimado)
- ✅ **FPS**: Velocidad máxima que permite el hardware
- ✅ **Resolución configurada**: 1280x720 (upscaled desde 720p nativo)
- ✅ **Estabilidad**: Sin congelamientos ni lag perceptible

### Configuración Técnica Actual
```python
# Configuración de cámara
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# MediaPipe Pose (CPU-optimized)
self.pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
    model_complexity=1  # CPU mode
)
```

### Problemas Identificados
- ⚠️ **Detección de landmarks en tobillo**: Problemas específicos de precisión
- ℹ️ **Movimientos rápidos**: No es crítico porque el usuario se mantiene estático durante el procesamiento final

---

## 🎯 PRIORIDADES DE OPTIMIZACIÓN (En orden de importancia)

### 1. 🎯 **Precisión de Mediciones** (CRÍTICO)
- Cálculo exacto de ángulos articulares
- Detección confiable de landmarks
- Sistema de medición tipo goniómetro digital (0° a 180°)

### 2. ⚡ **Mínima Latencia** (MUY IMPORTANTE)
- Tiempo de respuesta < 50ms
- Feedback visual inmediato
- Sincronización precisa entre movimiento real y visualización

### 3. 🚀 **Máximo FPS Posible** (IMPORTANTE)
- Aprovechar al máximo la capacidad del i7-14650HX
- Mantener fluidez constante (30-60 FPS)
- Procesamiento eficiente en CPU

### 4. 🎨 **Calidad Visual** (DESEABLE)
- Dibujos suaves y claros
- Antialiasing en visualizaciones
- Interface informativa y profesional

### 5. 🔋 **Bajo Consumo de Batería** (OPCIONAL)
- Optimización para uso prolongado en laptop
- No crítico pero deseable

---

## 🧵 ARQUITECTURA DE THREADING Y GESTIÓN DE HILOS

### Estrategia General: Threading Selectivo y Controlado

Para este proyecto, **NO necesitamos threading complejo**. La estrategia es usar threads de manera **selectiva y específica** para operaciones que bloquean sin afectar el procesamiento principal.

### ⚡ DECISIÓN CLAVE: MÁXIMO 4-5 THREADS ACTIVOS

**Razón**: El i7-14650HX tiene 16 núcleos (6P+8E), pero:
- MediaPipe Pose ya usa multithreading interno (3-4 threads)
- OpenCV ya tiene paralelización interna
- **Más threads ≠ Más velocidad** (puede empeorar por context switching)

---

### 📋 THREADS DEL SISTEMA (Total: 4 threads principales)

#### **Thread 1: MAIN (Análisis de Video)** 🎥
```python
# Thread principal - NO BLOQUEANTE
while True:
    ret, frame = cap.read()
    results = pose.process(frame)      # MediaPipe (usa sus propios threads)
    angles = calculate_angles(results)
    validate_posture(results)          # Genera eventos de voz
    render_display(frame, angles)
    cv2.imshow('BIOTRACK', frame)
```

**Responsabilidades**:
- Captura de frames
- Procesamiento con MediaPipe
- Cálculo de ángulos
- Renderizado visual
- Detección de eventos (postura, ROM, etc.)

**Prioridad**: HIGHEST (Real-time)
**FPS objetivo**: 45-60
**NO debe bloquearse NUNCA**

---

#### **Thread 2: VOICE (Text-to-Speech)** 🎤
```python
# Thread daemon independiente
class VoiceThread(threading.Thread):
    def __init__(self, message_queue):
        super().__init__(daemon=True)
        self.queue = message_queue
        self.tts_engine = pyttsx3.init()
        
    def run(self):
        while True:
            if self.queue.should_speak_now():
                message = self.queue.get_next_message()
                if message:
                    self.tts_engine.say(message)
                    self.tts_engine.runAndWait()  # BLOCKING (solo en este thread)
            time.sleep(0.5)  # Polling cada 500ms
```

**Responsabilidades**:
- Reproducir mensajes de voz
- Gestionar cola de mensajes
- Controlar throttling (mín 3s entre mensajes)

**Prioridad**: LOW (puede esperar)
**Daemon**: TRUE (muere con el programa)
**Bloqueos**: Permitidos (no afecta main thread)

---

#### **Thread 3: ESP32 SERIAL (Comunicación con Hardware)** 🔧
```python
# Thread para comunicación serial USB
class ESP32SerialThread(threading.Thread):
    def __init__(self, port, baudrate=115200):
        super().__init__(daemon=True)
        self.serial = serial.Serial(port, baudrate)
        self.command_queue = queue.Queue()
        
    def run(self):
        while True:
            if not self.command_queue.empty():
                command = self.command_queue.get()
                self.serial.write(command.encode())
                response = self.serial.readline()
                # Procesar respuesta
            time.sleep(0.1)  # Polling cada 100ms
```

**Responsabilidades**:
- Enviar comandos al ESP32 (ajustar altura de cámara)
- Recibir confirmaciones del ESP32
- Gestionar cola de comandos

**Prioridad**: MEDIUM
**Daemon**: TRUE
**Uso**: Solo cuando se ajusta altura (no durante análisis activo)

---

#### **Thread 4: FLASK SERVER (Solo en modo web)** 🌐
```python
# Thread automático de Flask
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        threaded=True,     # Flask usa ThreadingMixIn
        debug=False        # NO usar debug=True (duplica threads)
    )
```

**Responsabilidades**:
- Servir requests HTTP
- WebSocket/AJAX para comunicación con frontend
- Streaming de video (si aplica)

**Prioridad**: MEDIUM
**Threads internos**: Flask crea 1 thread por request HTTP
**Control**: Limitado (Flask lo maneja internamente)

---

### 🚫 THREADS QUE **NO** USAREMOS

#### ❌ Thread separado para captura de video
**Razón**: `cap.read()` es muy rápido (5-10ms) y OpenCV ya está optimizado. Agregar thread aquí añade complejidad sin beneficio.

#### ❌ Thread separado para renderizado
**Razón**: `cv2.imshow()` es nativo y usa buffers internos. No necesita thread separado.

#### ❌ Thread pool para procesamiento paralelo de frames
**Razón**: Analizamos 1 persona con 1 cámara en tiempo real. No hay paralelización posible de frames individuales.

#### ❌ Thread para cálculos de ángulos
**Razón**: Los cálculos matemáticos (arctan2, dot product) toman <1ms. No justifica overhead de threading.

---

### 🔒 SINCRONIZACIÓN Y COMUNICACIÓN ENTRE THREADS

#### **1. Main → Voice (Productor → Consumidor)**
```python
# Thread-safe queue
from voice_system.message_queue import VoiceMessageQueue

# En Main Thread
voice_queue = VoiceMessageQueue(min_interval=3.0)
voice_queue.add_message("Levanta el brazo más alto", priority='NORMAL')

# Voice Thread consume automáticamente
```

**Mecanismo**: Cola thread-safe (`collections.deque` con locks internos)
**Sincronización**: Lock-free (deque es thread-safe para append/pop)

#### **2. Main → ESP32 (Comandos ocasionales)**
```python
# Thread-safe queue
import queue

esp32_queue = queue.Queue()  # Thread-safe nativo de Python

# En Main Thread
esp32_queue.put("HEIGHT:100")

# ESP32 Thread consume
command = esp32_queue.get()  # Blocking (pero en thread separado)
```

**Mecanismo**: `queue.Queue()` (thread-safe nativo)
**Sincronización**: Locks internos de Queue

#### **3. Flask ↔ Main (Comunicación web)**
```python
# Uso de variables globales con locks
import threading

# Global state con lock
state_lock = threading.Lock()
current_rom = 0
current_angle = 0

# En Main Thread (actualizar)
with state_lock:
    current_rom = max_angle

# En Flask route (leer)
@app.route('/api/current_rom')
def get_rom():
    with state_lock:
        return jsonify({'rom': current_rom})
```

**Mecanismo**: Lock explícito para variables compartidas
**Sincronización**: `threading.Lock()`

---

### 📊 DIAGRAMA DE THREADING

```
┌─────────────────────────────────────────────────────────┐
│  MAIN THREAD (ANÁLISIS DE VIDEO) - HIGHEST PRIORITY     │
│  ↓ Captura → MediaPipe → Ángulos → Validación → Display│
│  ↓ FPS: 45-60                                           │
│  ↓ NO BLOQUEANTE                                        │
└───────────────┬─────────────────────┬───────────────────┘
                │                     │
                │ Events              │ Events
                ↓                     ↓
    ┌───────────────────┐    ┌──────────────────┐
    │  VOICE THREAD     │    │  ESP32 THREAD    │
    │  (Daemon)         │    │  (Daemon)        │
    │  Priority: LOW    │    │  Priority: MED   │
    │  ↓ TTS Engine     │    │  ↓ Serial USB    │
    │  ↓ BLOQUEANTE     │    │  ↓ Commands      │
    │  (Solo aquí)      │    │  (Ocasional)     │
    └───────────────────┘    └──────────────────┘

    ┌──────────────────────────────────────────┐
    │  FLASK SERVER (Solo modo web)            │
    │  ↓ HTTP Requests                         │
    │  ↓ 1 thread por request                  │
    │  ↓ Lee estado con locks                  │
    └──────────────────────────────────────────┘
```

---

### ⚡ IMPACTO EN RENDIMIENTO

| Thread | CPU Usage | Impacto en FPS | Notas |
|--------|-----------|----------------|-------|
| MAIN | 60-80% (1 core) | Base (45-60 FPS) | MediaPipe usa internamente 3-4 cores |
| VOICE | 5-10% (picos) | <2% | Solo cuando habla (cada 3s mín.) |
| ESP32 | <1% | 0% | Solo durante ajuste de altura |
| FLASK | 5-15% | 0% | En core separado |
| **TOTAL** | ~70-90% | **FPS: 43-58** | <5% overhead vs. sin threads |

---

### 🎯 REGLAS DE ORO PARA THREADING EN BIOTRACK

1. ✅ **MAIN thread NUNCA se bloquea** → Garantiza FPS constante
2. ✅ **Threads daemon** para tareas secundarias → Mueren con el programa
3. ✅ **Colas thread-safe** para comunicación → Sin race conditions
4. ✅ **Throttling en Voice** (mín 3s) → Evita saturación
5. ✅ **Locks solo para variables globales compartidas** → Flask ↔ Main
6. ❌ **NO crear/destruir threads en runtime** → Overhead y memory leaks
7. ❌ **NO usar multiprocessing** → Overhead de IPC innecesario
8. ❌ **NO paralelizar MediaPipe** → Ya está optimizado internamente

---

### 🔧 IMPLEMENTACIÓN PRÁCTICA

#### **Ejemplo: Inicialización en `app.py`**
```python
import threading
from voice_system.tts_engine import VoiceThread
from hardware.esp32_serial import ESP32SerialThread

# Inicializar threads
voice_thread = VoiceThread(voice_queue)
voice_thread.start()  # Daemon automático

esp32_thread = ESP32SerialThread(port='COM3')
esp32_thread.start()  # Daemon automático

# Main loop continúa sin cambios
while True:
    # Procesamiento de video...
    pass

# Threads mueren automáticamente al salir
```

#### **Ejemplo: Agregar mensaje de voz desde Main**
```python
# En cualquier parte del análisis
if torso_tilted:
    voice_queue.add_message(
        "Evita inclinar el tronco hacia adelante",
        priority='HIGH'
    )
    # NO espera respuesta, continúa inmediatamente
```

---

### 🧪 TESTING Y DEBUGGING DE THREADS

```python
# Verificar threads activos
import threading
print(f"Threads activos: {threading.active_count()}")
for t in threading.enumerate():
    print(f"  - {t.name} (daemon={t.daemon})")

# Ejemplo de output esperado:
# Threads activos: 4
#   - MainThread (daemon=False)
#   - VoiceThread (daemon=True)
#   - ESP32SerialThread (daemon=True)
#   - Thread-1 (daemon=True)  # Flask workers
```

---

### 📚 RECURSOS Y LIBRERÍA

**Threading nativo de Python**:
```python
import threading
import queue
from collections import deque
```

**NO necesitamos**:
- ❌ `multiprocessing` (overhead de IPC)
- ❌ `asyncio` (complejidad innecesaria)
- ❌ `concurrent.futures` (overkill para este caso)

**Justificación**: Threading básico de Python es suficiente y eficiente para nuestro caso de uso.

---

## 💾 GESTIÓN DE DATOS Y ALMACENAMIENTO

### Durante la Sesión (Tiempo Real)
- ❌ **NO grabar video** en disco duro o base de datos
- ✅ **Visualización en pantalla** en tiempo real
- ✅ **Procesamiento de últimos frames** para cálculo de promedios
- ✅ **Cálculo de ROM máximo** durante la sesión

### Procesamiento de Ángulos
- **Método**: Promedio de ángulos de los últimos frames
- **Objetivo**: Suavizar mediciones y reducir ruido
- **Usuario**: Se mantiene **estático** durante el procesamiento final
- **Velocidad de movimiento**: Lenta y controlada

### Almacenamiento Posterior
- ✅ **Guardar solo ROM máximo** en historial del usuario
- ✅ **Exportación a PDF**: Descarga posterior del historial
- ❌ **NO almacenar video**: Solo métricas numéricas

---

## 🔧 STACK TECNOLÓGICO

### Backend y Procesamiento
- **Python 3.x** (Anaconda environment: `biomecanico`)
- **OpenCV**: Captura y procesamiento de video
- **MediaPipe Pose**: Detección de puntos clave del cuerpo (landmarks)
- **NumPy**: Cálculos matemáticos de ángulos y vectores

### Frontend y Servidor
- **Flask**: Framework web para interfaz de usuario
- **HTML/CSS/JavaScript**: Templates y visualización
- **AJAX**: Comunicación asíncrona con backend
- **SQLite**: Base de datos para almacenamiento de usuarios y mediciones

### Sistema de Voz Guiada (NUEVO)
- **pyttsx3**: Motor Text-to-Speech offline (Windows SAPI5)
- **gTTS**: Google Text-to-Speech (alternativa online)
- **pygame/playsound**: Reproducción de audio
- **Threading**: Ejecución asíncrona de voz para no bloquear análisis

### Estructura del Proyecto
```
biomechanical_analysis/
├── analyzers/                      # Analizadores de articulaciones
│   ├── base_analyzer.py           # Clase base con integración de voz
│   ├── shoulder_profile.py
│   ├── shoulder_frontal.py
│   ├── elbow_profile.py
│   ├── hip_profile.py
│   ├── hip_frontal.py
│   ├── knee_profile.py
│   ├── ankle_profile.py
│   ├── ankle_frontal.py
│   ├── rom_evaluator.py           # Evaluador de ROM con feedback
│   └── posture_validator.py       # Detector de errores de postura
├── core/
│   ├── angle_debugger.py
│   ├── base_analyzer.py
│   ├── camera_manager.py
│   ├── exercise_guide_base.py
│   ├── fixed_references.py
│   ├── mediapipe_config.py
│   └── orientation_detector.py
├── utils/
│   ├── validators.py
│   ├── decorators.py
│   ├── pdf_generator.py
│   ├── rom_standards.py
│   ├── helpers.py
│   └── audio_utils.py             # Utilidades de audio
└── tests/
    ├── test_shoulder_frontal.py
    ├── test_shoulder_profile.py
    ├── test_elbow_profile.py
    ├── test_hip_frontal.py
    ├── test_hip_profile.py
    ├── test_knee_profile.py
    ├── test_ankle_profile.py
    └── test_ankle_frontal.py

biomechanical_web_interface/
├── app.py
├── config.py
├── requirements.txt
├── instance/
│   └── biotrack.db                # Base de datos SQLite
├── models/                         # Modelos de datos
│   ├── user.py
│   ├── measurement.py
│   ├── exercise.py
│   ├── session.py
│   └── voice_feedback.py          # Modelo de retroalimentación de voz
├── controllers/                    # Controladores
│   ├── auth_controller.py
│   ├── measurement_controller.py
│   ├── history_controller.py
│   ├── esp32_controller.py
│   ├── pdf_controller.py
│   └── voice_controller.py        # Control de mensajes de voz
├── voice_system/                   # NUEVO: Sistema de voz guiada
│   ├── tts_engine.py              # Motor Text-to-Speech
│   ├── audio_player.py            # Reproductor de audio
│   ├── message_queue.py           # Cola de mensajes con prioridades
│   ├── voice_phrases.py           # Frases predefinidas por ejercicio
│   └── speech_config.py           # Configuración de voz
├── audio_cache/                    # NUEVO: Cache de audios
│   ├── generated/                 # Audios generados dinámicamente
│   └── prerecorded/               # Audios pregrabados por ejercicio
│       ├── shoulder_profile/
│       ├── shoulder_frontal/
│       ├── elbow_profile/
│       ├── hip_profile/
│       ├── hip_frontal/
│       ├── knee_profile/
│       ├── ankle_profile/
│       └── ankle_frontal/
├── hardware/                       # Control de hardware
│   ├── esp32_serial.py            # Comunicación serial con ESP32
│   ├── camera_controller.py       # Control de altura de cámara
│   └── arduino_sketch/
│       └── camera_height_control.ino
├── routes/                         # Rutas Flask
│   ├── main.py
│   ├── auth.py
│   ├── measurement.py
│   ├── history.py
│   ├── calibration.py
│   └── api.py
├── static/
│   ├── css/
│   │   ├── main.css
│   │   ├── dashboard.css
│   │   ├── measurement.css
│   │   ├── history.css
│   │   └── voice_controls.css     # Estilos para controles de voz
│   ├── js/
│   │   ├── main.js
│   │   ├── video_stream.js
│   │   ├── measurement.js
│   │   ├── charts.js
│   │   ├── esp32_control.js
│   │   ├── history.js
│   │   └── voice_feedback.js      # Reproducción de audio frontend
│   └── images/
│       ├── exercise_icons/
│       └── feedback/
│           ├── optimal.svg
│           ├── good.svg
│           ├── limited.svg
│           ├── poor.svg
│           ├── voice_on.svg       # Íconos de voz
│           └── voice_off.svg
└── templates/
    ├── base.html
    ├── auth/
    ├── dashboard/
    ├── measurement/
    │   ├── select_exercise.html
    │   ├── calibrate.html
    │   ├── live_analysis.html     # Con controles de voz
    │   └── results.html
    ├── history/
    └── components/
        ├── navbar.html
        ├── feedback_card.html
        ├── rom_gauge.html
        ├── exercise_card.html
        └── voice_controls.html    # Panel de control de voz
```

---

## 🚀 DECISIONES TÉCNICAS CLAVE

### ✅ Uso de CPU en lugar de GPU
**Decisión**: Mantener procesamiento en CPU (i7-14650HX)  
**Razón**: 
- MediaPipe Pose está optimizado para inferencia en CPU
- Para 1 persona @ 720p, CPU es más eficiente que GPU
- Evita overhead de transferencia CPU↔GPU
- No requiere instalación de CUDA/cuDNN (14GB)
- Mayor portabilidad del código
- Menor consumo de batería en laptop

**RTX 4060 NO se utiliza** (decisión consciente y correcta para este caso de uso)

### ✅ Resolución de Procesamiento
**Configuración actual**: 1280x720 (upscaled)  
**Recomendación futura**: Procesar a 640x480 nativos y escalar solo para display
**Ganancia esperada**: +40% FPS con misma precisión

### ✅ Sistema de Medición Goniómetro Digital
**Concepto**: Todos los ángulos en rango 0° a 180° (siempre positivos)
- **0°**: Posición neutra (brazo abajo, pegado al cuerpo)
- **90°**: Posición horizontal/perpendicular
- **180°**: Extensión máxima (brazo arriba)

**Backend**: Mantiene signos internos (+flexión, -extensión) para distinguir direcciones  
**Frontend**: Muestra `abs()` para simular goniómetro físico

---

## 💡 OPTIMIZACIONES PROPUESTAS (No implementadas aún)

### Nivel 1: Optimizaciones Básicas (+30-50% rendimiento)
1. **Reducción de resolución de procesamiento**
   - Procesar MediaPipe a 640x480
   - Escalar landmarks de vuelta a resolución de display
   - Mantener calidad visual sin perder precisión

2. **Optimización de dibujos OpenCV**
   ```python
   # Usar LINE_4 en vez de LINE_AA (default)
   cv2.line(img, p1, p2, color, 2, cv2.LINE_4)
   ```

3. **Caché de cálculos repetitivos**
   - Normalización de vectores
   - Conversión de coordenadas
   - Colores según rangos de ángulos

### Nivel 2: Threading Avanzado (+50-80% rendimiento)
1. **Procesamiento en thread separado**
   - Pipeline producer-consumer
   - Desacoplar captura de procesamiento

2. **Display asíncrono**
   - Renderizado en thread independiente
   - Buffer circular de frames procesados

3. **Frame skipping inteligente**
   - Saltar frames cuando hay cola
   - Priorizar frames más recientes

### Nivel 3: Arquitectura Profesional (+100-150% rendimiento)
1. **Pipeline multi-thread completo**
   - Thread de captura
   - Thread de procesamiento MediaPipe
   - Thread de cálculos de ángulos
   - Thread de renderizado

2. **Memoria compartida optimizada**
   - Uso de `multiprocessing.shared_memory`
   - Reducción de copias de frames

3. **Predicción de landmarks**
   - Interpolación cuando MediaPipe es lento
   - Suavizado temporal con filtro Kalman

---

## 📝 FUNCIONALIDAD DEL MÓDULO ACTUAL (test_shoulder.py.py)

### Detección Automática de Orientación
El sistema detecta automáticamente si el usuario está:
- **PERFIL**: Analiza flexión/extensión de un hombro
- **FRONTAL**: Analiza abducción bilateral de ambos hombros

### Vista de PERFIL
- **Ángulo calculado**: Flexión/Extensión del hombro visible
- **Referencias**: Hombro → Cadera (vector vertical), Hombro → Codo (vector del brazo)
- **Rango**: 0° (brazo abajo) a 180° (brazo arriba)
- **Signo interno**: +flexión (adelante), -extensión (atrás)
- **Display**: Siempre positivo + etiqueta "FLEX"/"EXT"

### Vista FRONTAL
- **Ángulo calculado**: Abducción de ambos hombros simultáneamente
- **Referencias**: Hombro → Cadera (línea vertical), Hombro → Codo (vector del brazo)
- **Rango**: 0° (brazos pegados) a 180° (brazos arriba)
- **Visualización**: Barras verticales de progreso para cada brazo

### Elementos Visuales
- ✅ Skeleton completo del cuerpo (MediaPipe)
- ✅ Puntos clave destacados (hombro, cadera, codo)
- ✅ Líneas de referencia vectorial
- ✅ Ángulos en tiempo real junto a articulaciones
- ✅ Panel de información con estadísticas
- ✅ Barras de progreso de ROM
- ✅ Código de colores según rango de movimiento

### Controles de Usuario
- **Q**: Salir de la aplicación
- **R**: Reiniciar estadísticas (ROM máximo)

---

## 🔍 PROBLEMAS CONOCIDOS Y ÁREAS DE MEJORA

### 1. Detección de Landmarks en Tobillo ⚠️
**Problema**: MediaPipe tiene dificultad detectando landmarks del tobillo con precisión  
**Posibles causas**:
- Menor tamaño visual de la articulación
- Oclusión frecuente (pantalones, zapatos)
- Menor contraste con el fondo

**Soluciones propuestas**:
- Aumentar `min_detection_confidence` para tobillo
- Usar `model_complexity=2` selectivamente
- Implementar filtrado temporal (suavizado)
- Instrucciones específicas de vestimenta (ropa ajustada, descalzo)

### 2. Expansión a Otros Segmentos
**Desafío**: Crear arquitectura modular y escalable  
**Requisitos**:
- Clase base común para todos los analizadores
- Sistema de configuración por ejercicio (JSON)
- Detección automática de vista óptima por ejercicio
- Cálculos de ángulos específicos por articulación

### 3. Integración con Flask
**Pendiente**:
- Streaming de video procesado a navegador
- WebSocket o AJAX para comunicación en tiempo real
- Almacenamiento de ROM en base de datos/sesión
- Generación de PDF con historial

---

## 🎓 FLUJO DE TRABAJO TÍPICO

### Sesión de Análisis (Usuario)
1. Usuario accede a la interfaz web
2. Selecciona ejercicio/segmento a analizar
3. Sistema calcula altura óptima de cámara → ESP32 ajusta altura
4. **VOZ**: "Colócate de perfil. Vamos a medir la flexión de hombro"
5. Sistema detecta automáticamente orientación (PERFIL/FRONTAL)
6. **VOZ**: "Posición correcta. Puedes comenzar"
7. Usuario realiza movimiento **lentamente y de forma controlada**
8. **VOZ**: Guía en tiempo real ("Levanta el brazo más alto", "Excelente técnica")
9. **VOZ**: Correcciones si detecta errores ("Evita inclinar el tronco")
10. Usuario se mantiene **estático en posición final** durante procesamiento
11. Sistema calcula **promedio de últimos frames**
12. Se registra **ROM máximo** alcanzado
13. **VOZ**: "Has alcanzado 145 grados. Excelente ROM"
14. Resultados se guardan en historial del usuario
15. Usuario puede descargar reporte en PDF posteriormente

### Procesamiento Backend (con Voz)
```
Captura Frame → MediaPipe Pose → Detección Orientación → 
Cálculo Ángulos → Validación de Postura → 
Actualizar Estadísticas → Generar Mensaje de Voz (thread) →
Renderizado Visual → Display
```

### Sistema de Voz Guiada (Multithreading)
```
Thread Principal (Análisis)
    ↓
Detecta evento/error → Agrega mensaje a cola con prioridad
    ↓
Thread de Voz (independiente)
    ↓
Verifica cola cada N segundos → Reproduce mensaje TTS
    ↓
NO bloquea procesamiento de video (FPS mantiene 45-60)
```

---

## 📚 REFERENCIAS TÉCNICAS

### MediaPipe Pose Landmarks
```
Puntos clave utilizados:
- NOSE (0)
- LEFT_SHOULDER (11) / RIGHT_SHOULDER (12)
- LEFT_ELBOW (13) / RIGHT_ELBOW (14)
- LEFT_WRIST (15) / RIGHT_WRIST (16)
- LEFT_HIP (23) / RIGHT_HIP (24)
- LEFT_KNEE (25) / RIGHT_KNEE (26)
- LEFT_ANKLE (27) / RIGHT_ANKLE (28)
```

### Fórmulas de Cálculo de Ángulos

#### Método 1: Producto Punto (ángulo entre vectores)
```python
cos(θ) = (v1 · v2) / (|v1| × |v2|)
θ = arccos(cos(θ))
```

#### Método 2: Producto Cruz (dirección del ángulo)
```python
cross_product = v1.x × v2.y - v1.y × v2.x
signo = +1 si cross_product > 0 else -1
```

### Sistema de Coordenadas MediaPipe
- **Origen**: Esquina superior izquierda
- **X**: 0 (izquierda) a 1 (derecha) - normalizado
- **Y**: 0 (arriba) a 1 (abajo) - normalizado
- **Z**: Profundidad (no utilizada actualmente)

---

## 🚧 PRÓXIMOS PASOS Y ROADMAP

### Fase 1: Optimización del Módulo de Hombro ✅ (En progreso)
- [ ] Implementar reducción de resolución de procesamiento
- [ ] Optimizar dibujos OpenCV
- [ ] Agregar buffer de frames para promediado
- [ ] Implementar sistema de profiling (FPS, latencia)
- [ ] Threading básico (captura + procesamiento)
- [ ] **Sistema de voz guiada con TTS**
- [ ] **Validador de postura en tiempo real**

### Fase 2: Modularización y Arquitectura
- [ ] Crear clase base `BaseJointAnalyzer` con hooks de voz
- [ ] Extraer lógica común de detección de orientación
- [ ] Sistema de configuración por ejercicio (JSON)
- [ ] Factory pattern para crear analizadores
- [ ] **Integrar PostureValidator en base_analyzer**
- [ ] **Sistema de frases de voz por ejercicio**

### Fase 3: Expansión a Otros Segmentos
- [ ] Implementar analizador de codo con voz
- [ ] Implementar analizador de cadera con voz
- [ ] Implementar analizador de rodilla con voz
- [ ] Implementar analizador de tobillo (con mejoras especiales) con voz
- [ ] **Grabar audios pregrabados profesionales (opcional)**

### Fase 4: Integración Web Completa
- [ ] Streaming de video a navegador
- [ ] Almacenamiento de ROM en base de datos
- [ ] **Almacenamiento de log de mensajes de voz por sesión**
- [ ] Generación de reportes PDF
- [ ] Dashboard de progreso del usuario
- [ ] Sistema de login y perfiles
- [ ] **Control ESP32 para altura de cámara vía serial USB**

### Fase 5: Características Avanzadas
- [ ] Comparación con valores normativos
- [ ] Detección de compensaciones posturales
- [ ] Exportación de datos (CSV, JSON)
- [ ] Modo de calibración personalizada
- [ ] **Modo silencioso / control de volumen de voz**
- [ ] **Estadísticas de errores de postura más comunes**
- [ ] Integración con dispositivos externos (opcional)

---

## 📊 MÉTRICAS DE ÉXITO

### Rendimiento Técnico
- ✅ FPS constante > 30 (ideal: 45-60)
- ✅ Latencia < 50ms
- ✅ Precisión de ángulos ±2° vs goniómetro físico
- ✅ Detección de landmarks > 95% del tiempo

### Experiencia de Usuario
- ✅ Interface intuitiva y profesional
- ✅ Feedback visual claro y en tiempo real
- ✅ Instrucciones claras y comprensibles
- ✅ Reportes informativos y descargables

### Escalabilidad
- ✅ Fácil adición de nuevos ejercicios
- ✅ Código modular y mantenible
- ✅ Documentación completa
- ✅ Sistema portable (sin dependencias de GPU)

---

## 🔐 CONSIDERACIONES IMPORTANTES

### Limitaciones del Sistema
1. **Educativo, NO diagnóstico médico**: No reemplaza evaluación profesional
2. **Cámara única**: Limitaciones en profundidad (Z)
3. **Iluminación**: Requiere buena iluminación para detección precisa
4. **Vestimenta**: Ropa ajustada mejora detección de landmarks
5. **Fondo**: Fondo despejado mejora precisión

### Requisitos del Entorno
- Espacio mínimo: 2m × 2m frente a la cámara
- Iluminación: Natural o artificial brillante y uniforme
- Fondo: Preferiblemente liso y contrastante
- Vestimenta: Ropa ajustada, colores contrastantes

### Privacidad y Datos
- Video NO se almacena en disco
- Solo se guardan métricas numéricas (ángulos)
- Procesamiento local (no envío a servidores externos)
- Cumplimiento con privacidad de datos de usuario

---

## 📖 GLOSARIO TÉCNICO

- **ROM**: Range of Motion (Rango de Movimiento)
- **Landmark**: Punto clave anatómico detectado por MediaPipe
- **Goniómetro**: Instrumento de medición de ángulos articulares
- **Flexión**: Movimiento que reduce el ángulo entre segmentos (hacia adelante/arriba)
- **Extensión**: Movimiento que aumenta el ángulo entre segmentos (hacia atrás)
- **Abducción**: Movimiento que aleja un miembro del cuerpo (lateral)
- **Aducción**: Movimiento que acerca un miembro al cuerpo
- **FPS**: Frames Per Second (cuadros por segundo)
- **Latencia**: Tiempo de retraso entre acción y respuesta del sistema

---

## 📞 INFORMACIÓN DEL PROYECTO

- **Nombre**: BIOTRACK - Sistema de Análisis Biomecánico
- **Versión actual**: V10_CLEAN
- **Repositorio**: CLEAN_VERSION_BIOTRACK
- **Owner**: MarianaCO7
- **Branch**: main
- **Última actualización**: Noviembre 14, 2025

---

## 📝 NOTAS FINALES

### Decisiones Conscientes Tomadas
1. ✅ **CPU en vez de GPU**: Más eficiente para este caso de uso
2. ✅ **Cámara 720p**: Suficiente precisión vs. procesamiento
3. ✅ **MediaPipe model_complexity=1**: Balance óptimo velocidad/precisión
4. ✅ **Sistema goniómetro (0-180°)**: Familiar para usuarios médicos/educativos
5. ✅ **No almacenar video**: Privacidad y eficiencia de almacenamiento
6. ✅ **Threading selectivo (4 threads)**: Balance rendimiento/complejidad
7. ✅ **TTS offline (pyttsx3)**: No requiere internet, menor latencia
8. ✅ **Daemon threads para voz/ESP32**: Simplicidad en gestión de recursos

### Lecciones Aprendidas
- Hardware potente no siempre = mejor solución
- Optimización prematura vs. optimización necesaria
- Importancia de entender el caso de uso real
- Balance entre precisión y velocidad
- Detección de landmarks varía según articulación
- **Threading simple > Threading complejo** para este proyecto
- **Voz en thread separado preserva FPS del análisis**
- **Cola de mensajes evita saturación de voz**

---

**Este documento debe ser actualizado conforme el proyecto evolucione.**

**Uso**: Copiar y pegar este contexto en nuevos chats para mantener continuidad del desarrollo.
