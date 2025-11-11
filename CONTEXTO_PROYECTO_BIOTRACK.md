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

### Estructura del Proyecto
```
biomechanical_analysis/
├── core/
│   ├── angle_debugger.py
│   ├── base_analyzer.py
│   ├── camera_manager.py
│   ├── exercise_guide_base.py
│   ├── fixed_references.py
│   ├── mediapipe_config.py
│   └── orientation_detector.py
├── exercises/
├── guides/
│   └── neck_exercise_guide.py
├── joints/
└── tests/
    └── test_shoulder.py.py  ← MÓDULO ACTUAL

biomechanical_web_interface/
├── app.py
├── config/
│   ├── config_loader.py
│   ├── exercises.json
│   └── logging_config.py
├── handlers/
├── static/
│   ├── css/
│   ├── js/
│   └── images/
└── templates/
    ├── analysis.html
    ├── dashboard.html
    ├── profile.html
    └── ...
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
3. Se posiciona frente a la cámara
4. Sistema detecta automáticamente orientación (PERFIL/FRONTAL)
5. Usuario realiza movimiento **lentamente y de forma controlada**
6. Usuario se mantiene **estático en posición final** durante procesamiento
7. Sistema calcula **promedio de últimos frames**
8. Se registra **ROM máximo** alcanzado
9. Resultados se guardan en historial del usuario
10. Usuario puede descargar reporte en PDF posteriormente

### Procesamiento Backend
```
Captura Frame → MediaPipe Pose → Detección Orientación → 
Cálculo Ángulos → Actualizar Estadísticas → 
Renderizado Visual → Display
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

### Fase 2: Modularización y Arquitectura
- [ ] Crear clase base `BaseJointAnalyzer`
- [ ] Extraer lógica común de detección de orientación
- [ ] Sistema de configuración por ejercicio (JSON)
- [ ] Factory pattern para crear analizadores

### Fase 3: Expansión a Otros Segmentos
- [ ] Implementar analizador de codo
- [ ] Implementar analizador de cadera
- [ ] Implementar analizador de rodilla
- [ ] Implementar analizador de tobillo (con mejoras especiales)

### Fase 4: Integración Web Completa
- [ ] Streaming de video a navegador
- [ ] Almacenamiento de ROM en base de datos
- [ ] Generación de reportes PDF
- [ ] Dashboard de progreso del usuario
- [ ] Sistema de login y perfiles

### Fase 5: Características Avanzadas
- [ ] Comparación con valores normativos
- [ ] Detección de compensaciones posturales
- [ ] Exportación de datos (CSV, JSON)
- [ ] Modo de calibración personalizada
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
- **Última actualización**: Noviembre 11, 2025

---

## 📝 NOTAS FINALES

### Decisiones Conscientes Tomadas
1. ✅ **CPU en vez de GPU**: Más eficiente para este caso de uso
2. ✅ **Cámara 720p**: Suficiente precisión vs. procesamiento
3. ✅ **MediaPipe model_complexity=1**: Balance óptimo velocidad/precisión
4. ✅ **Sistema goniómetro (0-180°)**: Familiar para usuarios médicos/educativos
5. ✅ **No almacenar video**: Privacidad y eficiencia de almacenamiento

### Lecciones Aprendidas
- Hardware potente no siempre = mejor solución
- Optimización prematura vs. optimización necesaria
- Importancia de entender el caso de uso real
- Balance entre precisión y velocidad
- Detección de landmarks varía según articulación

---

**Este documento debe ser actualizado conforme el proyecto evolucione.**

**Uso**: Copiar y pegar este contexto en nuevos chats para mantener continuidad del desarrollo.
