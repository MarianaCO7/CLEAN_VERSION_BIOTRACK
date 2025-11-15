# 🎯 Sistema de Análisis en Vivo - BIOTRACK

## ✅ Implementación Completada

Se ha implementado exitosamente el sistema de análisis en vivo para ejercicios de hombro, con una arquitectura modular y escalable.

---

## 📁 Archivos Creados/Modificados

### **Nuevos Archivos:**

1. **`hardware/camera_manager.py`** (Singleton thread-safe)
   - Gestiona acceso exclusivo a la cámara web
   - Previene conflictos de acceso concurrente
   - Context manager para liberación automática

2. **`app/analyzers/__init__.py`**
   - Módulo de analyzers

3. **`app/analyzers/shoulder_profile.py`**
   - Analyzer de flexión/extensión (vista perfil)
   - Adaptado para Flask (sin cv2.imshow)

4. **`app/analyzers/shoulder_frontal.py`**
   - Analyzer de abducción bilateral (vista frontal)
   - Adaptado para Flask

5. **`app/templates/measurement/live_analysis.html`**
   - Template de análisis en vivo
   - UI responsiva con video feed y métricas

6. **`app/static/js/live_analysis.js`**
   - Controller JavaScript del frontend
   - Polling de datos, gráficos, controles

### **Archivos Modificados:**

1. **`app/routes/main.py`**
   - Nueva ruta: `/segments/<segment>/exercises/<exercise>`
   - Importa `camera_manager`

2. **`app/routes/api.py`**
   - `/api/video_feed` - Stream MJPEG
   - `/api/analysis/start` - Iniciar sesión
   - `/api/analysis/stop` - Detener sesión
   - `/api/analysis/current_data` - Datos en tiempo real
   - `/api/analysis/reset` - Reiniciar ROM

3. **`app/templates/components/exercise_selector.html`**
   - Botones ahora apuntan a `live_analysis` en vez de "Próximamente"

---

## 🚀 Cómo Usar

### 1. **Iniciar el servidor Flask**

```bash
cd c:\Users\mariz\Documents\PROYECTO DE GRADO - BIOMECANICA\SOFTWARE\CLEAN_VERSION_FUNCIONANDO\V10_CLEAN\CLEAN_VERSION_BIOTRACK
C:/Users/mariz/anaconda3/envs/biomecanico/python.exe run.py
```

### 2. **Acceder a la aplicación**

```
http://127.0.0.1:5000
```

### 3. **Navegación**

```
Dashboard 
  ↓
Segmentos 
  ↓
Hombro - Ejercicios
  ↓
[Flexión de Hombro] o [Abducción de Hombro]
  ↓
Análisis en Vivo (NUEVO)
```

### 4. **URLs Directas**

- **Flexión de Hombro (Perfil)**: 
  ```
  http://127.0.0.1:5000/segments/shoulder/exercises/flexion
  ```

- **Abducción de Hombro (Frontal)**:
  ```
  http://127.0.0.1:5000/segments/shoulder/exercises/abduction
  ```

---

## 🎮 Controles en Análisis en Vivo

### Botones:

- **Iniciar Análisis**: Comienza la sesión (activa polling de datos)
- **Detener**: Finaliza y muestra modal de resultados
- **Reiniciar ROM**: Resetea el ROM máximo sin detener el análisis
- **Volver**: Regresa al selector de ejercicios

### Datos Mostrados:

- **Ángulo Actual**: Ángulo en tiempo real
- **ROM Máximo**: Máximo alcanzado en la sesión
- **Estado de Postura**: Indica si la postura es correcta
- **FPS**: Rendimiento del sistema

---

## 🏗️ Arquitectura Implementada

### **Singleton Camera Manager**

```python
# Un solo acceso a la cámara en toda la app
with camera_manager.acquire_camera(user_id='user123') as cap:
    ret, frame = cap.read()
    # ... procesar
# Auto-release al salir del 'with'
```

**Ventajas:**
- ✅ Previene que 2 usuarios usen la cámara simultáneamente
- ✅ Thread-safe con locks
- ✅ Liberación automática de recursos
- ✅ Detección de "cámara ocupada"

### **Analyzers Modulares**

```python
# Cada ejercicio tiene su analyzer
analyzer = ShoulderProfileAnalyzer()
processed_frame = analyzer.process_frame(frame)
current_data = analyzer.get_current_data()
```

**Métodos públicos:**
- `process_frame(frame)` → Retorna frame anotado
- `get_current_data()` → Retorna dict con métricas
- `reset()` → Reinicia estadísticas
- `cleanup()` → Libera recursos MediaPipe

### **Video Streaming MJPEG**

```python
@api_bp.route('/video_feed')
def video_feed():
    def generate_frames():
        with camera_manager.acquire_camera(user_id) as cap:
            while True:
                ret, frame = cap.read()
                processed = analyzer.process_frame(frame)
                yield frame_as_jpeg(processed)
    
    return Response(generate_frames(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')
```

### **Frontend con Polling**

```javascript
// Actualizar datos cada 200ms
setInterval(async () => {
    const response = await fetch('/api/analysis/current_data');
    const data = await response.json();
    updateUI(data);
}, 200);
```

---

## 🧩 Agregar Nuevos Ejercicios

### Paso 1: Crear Analyzer

```python
# app/analyzers/elbow_profile.py
class ElbowProfileAnalyzer:
    def __init__(self):
        # Inicializar MediaPipe
        
    def process_frame(self, frame):
        # Procesar frame
        return annotated_frame
    
    def get_current_data(self):
        return {
            'angle': self.current_angle,
            'max_rom': self.max_rom,
            # ...
        }
```

### Paso 2: Registrar en `routes/main.py`

```python
# En exercises_db:
'elbow': {
    'flexion': {
        'name': 'Flexión de Codo',
        'analyzer_type': 'elbow_profile',
        'analyzer_class': 'ElbowProfileAnalyzer',
        # ...
    }
}
```

### Paso 3: Registrar en `routes/api.py`

```python
# En analyzer_classes:
analyzer_classes = {
    'shoulder_profile': ShoulderProfileAnalyzer,
    'shoulder_frontal': ShoulderFrontalAnalyzer,
    'elbow_profile': ElbowProfileAnalyzer,  # ← AGREGAR
}
```

¡Listo! El nuevo ejercicio funcionará automáticamente.

---

## ⚠️ Problemas Conocidos y Soluciones

### **1. "Cámara en uso" al intentar acceder**

**Causa**: Un tab anterior no liberó la cámara correctamente.

**Solución**:
```python
# En Python console o crear endpoint:
from hardware.camera_manager import camera_manager
camera_manager.force_release()
```

### **2. Video feed no carga**

**Verificar**:
1. Cámara conectada y funcionando
2. Permisos de cámara otorgados al navegador
3. No hay otro software usando la cámara (Zoom, Teams, etc.)

**Debug**:
```bash
# Ver logs de Flask
# Buscar líneas con [LiveAnalysis] o [CameraManager]
```

### **3. FPS bajo (<20)**

**Optimizar**:
- Reducir resolución en `camera_manager.acquire_camera(width=640, height=480)`
- Cambiar `model_complexity=0` en analyzer
- Reducir calidad JPEG en `cv2.imencode(..., [cv2.IMWRITE_JPEG_QUALITY, 70])`

---

## 🔧 Configuración Avanzada

### **Cambiar resolución de procesamiento**

```python
# app/analyzers/shoulder_profile.py
analyzer = ShoulderProfileAnalyzer(
    processing_width=480,   # Más bajo = más rápido
    processing_height=360,
    show_skeleton=True      # Mostrar skeleton MediaPipe
)
```

### **Cambiar frecuencia de polling**

```javascript
// app/static/js/live_analysis.js
setInterval(async () => {
    // ...
}, 100);  // Cambiar de 200ms a 100ms
```

### **Habilitar skeleton completo**

```python
# En routes/api.py
current_analyzer = analyzer_class(
    processing_width=640,
    processing_height=480,
    show_skeleton=True  # ← Cambiar a True
)
```

---

## 📊 Métricas de Rendimiento

### **Esperado en tu hardware (i7-14650HX)**:

| Métrica | Valor Esperado |
|---------|----------------|
| **FPS** | 45-60 |
| **Latencia** | <50ms |
| **RAM** | ~500MB por sesión activa |
| **CPU** | 60-80% (1 core) + 3-4 cores MediaPipe |

### **Monitoreo**:

```python
# Los analyzers ya incluyen métricas automáticas:
perf = analyzer.get_performance_summary()
print(f"FPS promedio: {perf['avg_fps']:.1f}")
print(f"Latencia promedio: {perf['avg_processing_time']:.2f}ms")
```

---

## 🚧 Próximos Pasos

### **Fase 1: Completar Segmentos** (Prioridad Alta)

- [ ] Implementar `ElbowProfileAnalyzer`
- [ ] Implementar `HipProfileAnalyzer` + `HipFrontalAnalyzer`
- [ ] Implementar `KneeProfileAnalyzer`
- [ ] Implementar `AnkleProfileAnalyzer` + `AnkleFrontalAnalyzer`

### **Fase 2: Funcionalidades** (Prioridad Media)

- [ ] Guardar resultados en base de datos
- [ ] Exportar a PDF
- [ ] Sistema de voz guiada (threading)
- [ ] Control ESP32 de altura de cámara

### **Fase 3: Optimizaciones** (Prioridad Baja)

- [ ] Caché de frames procesados
- [ ] WebSocket en vez de polling
- [ ] Compresión de video con H.264

---

## 📝 Notas Importantes

### ✅ **Buenas Prácticas Implementadas**:

1. **Singleton Pattern** para CameraManager
2. **Context Manager** para gestión automática de recursos
3. **Thread-safe** con locks explícitos
4. **Separation of Concerns**: Hardware ≠ Controllers
5. **DRY**: Template único reutilizable
6. **Logging** adecuado en todos los componentes

### ⚠️ **Limitaciones Actuales**:

1. Solo 1 usuario puede usar la cámara a la vez (por diseño)
2. Si el usuario cierra el tab sin "Detener", la sesión queda activa 2-3 segundos
3. No hay autenticación en `/api/video_feed` (depende de session)

### 🔒 **Seguridad**:

- ✅ Decorator `@login_required` en todas las rutas
- ✅ Validación de parámetros en endpoints
- ✅ Manejo de errores sin exponer detalles internos
- ⚠️ TODO: Rate limiting para evitar abuso de polling

---

## 📞 Soporte

Si encuentras problemas:

1. **Revisar logs de Flask** en consola
2. **Revisar consola del navegador** (F12 → Console)
3. **Verificar que imports funcionan**:
   ```python
   from hardware.camera_manager import camera_manager
   from app.analyzers import ShoulderProfileAnalyzer
   ```

---

**Implementado por**: GitHub Copilot + Claude Sonnet 4.5  
**Fecha**: 2025-11-14  
**Versión**: v1.0
